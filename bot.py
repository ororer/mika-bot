import os
import re
import time
import threading
import http.server
import socketserver
import telebot
import yfinance as yf
from engine import PlaybookEngine
from mentor import get_mentor_analysis, get_mentor_chat_reply

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN אינו מוגדר.")

bot = telebot.TeleBot(BOT_TOKEN)

BOT_USERNAME = ""
BOT_ID = None
try:
    bot_user = bot.get_me()
    BOT_USERNAME = bot_user.username.lower() if bot_user.username else ""
    BOT_ID = bot_user.id
    print(f"[Bot Init] הבוט מחובר תחת המשתמש: @{BOT_USERNAME} (ID: {BOT_ID})", flush=True)
except Exception as e:
    print(f"[Bot Init] לא הצלחתי למשוך פרטי בוט: {e}", flush=True)

MARKET_CACHE = {}
CACHE_TTL = 300

HEBREW_TICKERS = {
    "טסלה": "TSLA",
    "אפל": "AAPL",
    "אנבידיה": "NVDA",
    "אמזון": "AMZN",
    "גוגל": "GOOGL",
    "מיקרוסופט": "MSFT",
    "מייקרוסופט": "MSFT",
    "מטא": "META"
}

def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    class QuietHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Chip is listening 24/7!")
        def log_message(self, format, *args):
            pass

    with socketserver.TCPServer(("", port), QuietHandler) as httpd:
        httpd.serve_forever()

def normalize_text(text: str) -> str:
    # נרמול כל סוגי הגרשים לגרש סטנדרטי
    return text.replace("’", "'").replace("`", "'").replace("״", '"')

def extract_ticker(text: str):
    clean_text = normalize_text(text)
    if BOT_USERNAME:
        clean_text = re.sub(rf"@{BOT_USERNAME}\b", "", clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r"@\w+_bot\b", "", clean_text, flags=re.IGNORECASE)

    # 1. חיפוש שם מניה בעברית
    for heb_name, ticker in HEBREW_TICKERS.items():
        if heb_name in clean_text:
            return ticker

    # 2. חיפוש טיקר עם סימן דולר (למשל: $NVDA)
    cashtag = re.findall(r'\$([A-Za-z]{1,5})\b', clean_text)
    if cashtag:
        return cashtag[0].upper()

    # 3. מילים באנגלית תוך התעלמות ממילות שיחה נפוצות
    words = re.findall(r'\b[A-Za-z]{1,5}\b', clean_text.upper())
    ignored = {
        "HI", "HELLO", "OK", "BUY", "SELL", "WAIT", "BOT", "HEY", "YES", "NO", 
        "CHIP", "WHAT", "AGENT", "MARKET", "PRO", "AND", "THE", "CAN", "YOU",
        "FOR", "HOW", "WHY", "NOW", "SEE", "GET", "NEW", "TOP"
    }

    for word in words:
        if word not in ignored:
            return word
    return None

def analyze_and_format(ticker_symbol: str) -> str:
    now = time.time()
    if ticker_symbol in MARKET_CACHE:
        cached = MARKET_CACHE[ticker_symbol]
        if now - cached["time"] < CACHE_TTL:
            return cached["result"]

    try:
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period="250d", interval="1d")

        if df.empty or len(df) < 155:
            return f"לא מצאתי מספיק נתונים על {ticker_symbol}. תוודא שזה טיקר תקין."

        engine = PlaybookEngine(df)
        result = engine.evaluate()

        curr = engine.df.iloc[-1]
        last_price = float(curr["Close"])
        rsi = float(curr["RSI_14"])
        sma150 = float(curr["SMA_150"])

        mentor_text = get_mentor_analysis(ticker_symbol, result, last_price, rsi, sma150)

        formatted_reply = (
            f"📊 צ'יפ בודק את {ticker_symbol}:\n"
            f"מחיר נוכחי: {last_price:.2f}$ | ממוצע 150: {sma150:.2f}$ | RSI: {rsi:.1f}\n"
            f"החלטת מנוע: {result.get('status')}\n\n"
            f"💡 דבר המנטור:\n"
            f"{mentor_text}"
        )

        MARKET_CACHE[ticker_symbol] = {"time": now, "result": formatted_reply}
        return formatted_reply
    except Exception as e:
        return f"שגיאה בבדיקת {ticker_symbol}: {e}"

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(
        message,
        "אהלן! אני צ'יפ 🤖📊\n"
        "הסיידקיק שלכם לניתוח טכני וסווינג לפי הפלייבוק.\n\n"
        "מה אפשר לעשות איתי?\n"
        "• שאלו אותי על מניה (למשל: 'מה עם אפל?', 'NVDA', '$TSLA')\n"
        "• דברו איתי חופשי: תייגו אותי, כתבו 'צ'יפ' או השיבו להודעה שלי!"
    )

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    raw_text = message.text or message.caption or ""
    user_text = raw_text.strip()
    if not user_text:
        return

    normalized = normalize_text(user_text)
    chat_type = message.chat.type  # 'private', 'group', 'supergroup'
    is_private = (chat_type == 'private')

    # בדיקת תשובה לבוט
    is_reply_to_bot = False
    if message.reply_to_message:
        reply_from = message.reply_to_message.from_user
        if reply_from and (reply_from.id == BOT_ID or (BOT_USERNAME and reply_from.username and reply_from.username.lower() == BOT_USERNAME)):
            is_reply_to_bot = True

    # בדיקת תיוג או פנייה ישירה לצ'יפ (כולל גרש חכם או רגיל)
    is_mentioned = (
        (BOT_USERNAME and f"@{BOT_USERNAME}" in normalized.lower()) or 
        ("צ'יפ" in normalized) or 
        ("ציפ" in normalized) or
        ("chip" in normalized.lower())
    )

    ticker = extract_ticker(user_text)

    # התעלמות אם זו קבוצה וההודעה אינה פנייה לבוט או בקשת מניה
    if not is_private and not ticker and not is_reply_to_bot and not is_mentioned:
        return

    try:
        bot.send_chat_action(message.chat.id, 'typing')
    except Exception:
        pass

    # ניתוח מניה או תשובת שיחה חופשית
    if ticker:
        reply = analyze_and_format(ticker)
    else:
        clean_text = normalized
        if BOT_USERNAME:
            clean_text = re.sub(rf"@{BOT_USERNAME}", "", clean_text, flags=re.IGNORECASE)
        clean_text = re.sub(r"\b(צ'יפ|ציפ|chip)\b", "", clean_text, flags=re.IGNORECASE).strip()
        
        reply = get_mentor_chat_reply(clean_text or normalized)

    bot.reply_to(message, reply)

if __name__ == "__main__":
    threading.Thread(target=run_health_server, daemon=True).start()
    print("...צ'יפ מחובר ומאזין בטלגרם (פרטי + קבוצות)", flush=True)
    bot.infinity_polling(timeout=15, long_polling_timeout=10)

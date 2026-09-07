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
    print(f"[Bot Init] מחובר בהצלחה: @{BOT_USERNAME} (ID: {BOT_ID})", flush=True)
except Exception as e:
    print(f"[Bot Init] שגיאה במשיכת נתוני בוט: {e}", flush=True)

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
    if not text:
        return ""
    return text.replace("’", "'").replace("`", "'").replace("״", '"')

def extract_ticker(text: str):
    clean_text = normalize_text(text)
    if BOT_USERNAME:
        clean_text = re.sub(rf"@{BOT_USERNAME}\b", "", clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r"@\w+_bot\b", "", clean_text, flags=re.IGNORECASE)

    # 1. חיפוש מניה בעברית
    for heb_name, ticker in HEBREW_TICKERS.items():
        if heb_name in clean_text:
            return ticker

    # 2. חיפוש טיקר עם $ (למשל: $NVDA)
    cashtag = re.findall(r'\$([A-Za-z]{1,5})\b', clean_text)
    if cashtag:
        return cashtag[0].upper()

    # 3. מילים באנגלית תוך סינון מילות דיבור נפוצות
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

@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_all_messages(message):
    raw_text = message.text or message.caption or ""
    user_text = raw_text.strip()
    if not user_text:
        return

    chat_type = message.chat.type
    chat_id = message.chat.id
    print(f"[Debug Incoming] הצ'אט: {chat_id} ({chat_type}) | הודעה: '{user_text}'", flush=True)

    normalized = normalize_text(user_text)
    is_private = (chat_type == 'private')

    # בדיקת תשובה לבוט
    is_reply_to_bot = False
    if message.reply_to_message and message.reply_to_message.from_user:
        rep_id = message.reply_to_message.from_user.id
        rep_user = (message.reply_to_message.from_user.username or "").lower()
        if rep_id == BOT_ID or (BOT_USERNAME and rep_user == BOT_USERNAME):
            is_reply_to_bot = True

    # בדיקת תיוג או שם
    is_mentioned = False
    if BOT_USERNAME and f"@{BOT_USERNAME}" in normalized.lower():
        is_mentioned = True
    elif any(k in normalized.lower() for k in ["צ'יפ", "ציפ", "chip"]):
        is_mentioned = True

    ticker = extract_ticker(user_text)

    print(f"[Debug Checks] פרטי: {is_private} | ריפליי: {is_reply_to_bot} | מתוייג: {is_mentioned} | מניה: {ticker}", flush=True)

    # אם זו קבוצה וההודעה אינה פנייה אליו
    if not is_private and not ticker and not is_reply_to_bot and not is_mentioned:
        print("[Debug Skipped] ההודעה לא מיועדת לבוט. דילוג.", flush=True)
        return

    try:
        bot.send_chat_action(chat_id, 'typing')
    except Exception as e:
        print(f"[Debug Error Action] {e}", flush=True)

    # הפקת מענה
    try:
        if ticker:
            print(f"[Debug Route] ניתוח מניה עבור {ticker}", flush=True)
            reply = analyze_and_format(ticker)
        else:
            print("[Debug Route] שיחת מנטור AI חופשית", flush=True)
            clean_text = normalized
            if BOT_USERNAME:
                clean_text = re.sub(rf"@{BOT_USERNAME}", "", clean_text, flags=re.IGNORECASE)
            clean_text = re.sub(r"\b(צ'יפ|ציפ|chip)\b", "", clean_text, flags=re.IGNORECASE).strip()
            reply = get_mentor_chat_reply(clean_text or normalized)

        bot.reply_to(message, reply)
        print("[Debug Success] תשובה נשלחה בהצלחה!", flush=True)
    except Exception as e:
        err_msg = f"אירעה שגיאה בעיבוד ההודעה: {e}"
        print(f"[Debug Exception] {err_msg}", flush=True)
        try:
            bot.reply_to(message, err_msg)
        except Exception:
            pass

if __name__ == "__main__":
    threading.Thread(target=run_health_server, daemon=True).start()
    print("...צ'יפ מחובר ומאזין בטלגרם (פרטי + קבוצות)", flush=True)
    bot.infinity_polling(timeout=20, long_polling_timeout=15)

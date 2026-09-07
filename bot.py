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

# שמירת שם המשתמש של הבוט כדי לזהות תיוגים בקבוצה
BOT_USERNAME = ""
try:
    bot_user = bot.get_me()
    BOT_USERNAME = bot_user.username.lower() if bot_user.username else ""
    print(f"[Bot Init] הבוט מחובר תחת המשתמש: @{BOT_USERNAME}", flush=True)
except Exception as e:
    print(f"[Bot Init] לא הצלחתי למשוך שם משתמש: {e}", flush=True)

# מטמון בזיכרון למשך 5 דקות לחיסכון בזמן
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

def extract_ticker(text: str):
    # 1. חיפוש שם מניה בעברית
    for heb_name, ticker in HEBREW_TICKERS.items():
        if heb_name in text:
            return ticker

    # 2. חיפוש טיקר באנגלית (1 עד 5 אותיות)
    words = re.findall(r'\b[A-Za-z]{1,5}\b', text.upper())
    ignored = {"HI", "HELLO", "OK", "BUY", "SELL", "WAIT", "BOT", "HEY", "YES", "NO", "CHIP", "WHAT"}
    if BOT_USERNAME:
        ignored.add(BOT_USERNAME.upper())

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
        "• שאלו אותי על מניה (למשל: 'מה עם אפל?', 'NVDA', 'טסלה')\n"
        "• בקבוצה: תייגו אותי או השיבו להודעה שלי בכל שאלה שתרצו!"
    )

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_text = message.text.strip() if message.text else ""
    if not user_text:
        return

    chat_type = message.chat.type  # 'private', 'group', 'supergroup'
    ticker = extract_ticker(user_text)

    # בדיקה האם ההודעה מיועדת לבוט
    is_private = (chat_type == 'private')
    is_reply_to_bot = (
        message.reply_to_message and 
        message.reply_to_message.from_user and 
        message.reply_to_message.from_user.is_bot
    )
    is_mentioned = (
        (BOT_USERNAME and f"@{BOT_USERNAME}" in user_text.lower()) or 
        ("צ'יפ" in user_text) or 
        ("ציפ" in user_text)
    )

    # אם זו קבוצה ולא מדובר במניה, בתיוג או בריפליי לבוט - לא מתערבים בשיחה
    if not is_private and not ticker and not is_reply_to_bot and not is_mentioned:
        return

    bot.send_chat_action(message.chat.id, 'typing')

    # אם זוהה טיקר/מניה – ניתוח טכני לפי הפלייבוק
    if ticker:
        reply = analyze_and_format(ticker)
    else:
        # ניקוי שם הבוט מהשאלה לצורך תשובת ה-AI
        clean_text = user_text
        if BOT_USERNAME:
            clean_text = re.sub(rf"@{BOT_USERNAME}", "", clean_text, flags=re.IGNORECASE)
        clean_text = re.sub(r"\b(צ'יפ|ציפ)\b", "", clean_text).strip()
        
        reply = get_mentor_chat_reply(clean_text or user_text)

    bot.reply_to(message, reply)

if __name__ == "__main__":
    threading.Thread(target=run_health_server, daemon=True).start()
    print("...צ'יפ מחובר ומאזין בטלגרם (פרטי + קבוצות)", flush=True)
    bot.infinity_polling(timeout=15, long_polling_timeout=10)

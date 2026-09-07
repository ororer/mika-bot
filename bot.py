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
            self.wfile.write(b"Chip is operational!")
        def log_message(self, format, *args):
            pass

    with socketserver.TCPServer(("", port), QuietHandler) as httpd:
        httpd.serve_forever()

def extract_ticker(text: str):
    for heb_name, ticker in HEBREW_TICKERS.items():
        if heb_name in text:
            return ticker

    words = re.findall(r'\b[A-Za-z]{1,5}\b', text.upper())
    ignored = {"HI", "HELLO", "OK", "BUY", "SELL", "WAIT", "BOT", "HEY", "YES", "NO", "CHIP", "WHAT"}
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
        "הסיידקיק שלך לניתוח טכני וסווינג לפי הפלייבוק.\n\n"
        "מה אפשר לעשות?\n"
        "• שלח לי שם מניה (כמו: 'מה עם מייקרוסופט?', 'NVDA', 'טסלה')\n"
        "• שאל שאלות חופשיות על ניהול סיכונים ואסטרטגיה."
    )

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_text = message.text.strip()
    ticker = extract_ticker(user_text)

    bot.send_chat_action(message.chat.id, 'typing')

    if ticker:
        reply = analyze_and_format(ticker)
    else:
        reply = get_mentor_chat_reply(user_text)

    bot.reply_to(message, reply)

if __name__ == "__main__":
    threading.Thread(target=run_health_server, daemon=True).start()
    print("...צ'יפ מחובר ומאזין בטלגרם", flush=True)
    bot.infinity_polling(timeout=15, long_polling_timeout=10)

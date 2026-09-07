import os
import re
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

# שרת דופק זעיר ברקע כדי לענות לדרישות השרת של Render
def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    class QuietHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Micha Bot is alive!")
        def log_message(self, format, *args):
            pass

    with socketserver.TCPServer(("", port), QuietHandler) as httpd:
        httpd.serve_forever()

def extract_ticker(text: str):
    words = re.findall(r'\b[A-Za-z]{1,5}\b', text.upper())
    ignored = {"HI", "HELLO", "OK", "BUY", "SELL", "WAIT", "BOT", "HEY", "YES", "NO"}
    for word in words:
        if word not in ignored:
            return word
    return None

def analyze_and_format(ticker_symbol: str) -> str:
    try:
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period="1y", interval="1d")

        if df.empty or len(df) < 155:
            return f"לא הצלחתי למשוך מספיק נתונים עבור {ticker_symbol}. ודא שזה טיקר תקין בוול סטריט."

        engine = PlaybookEngine(df)
        result = engine.evaluate()

        curr = engine.df.iloc[-1]
        last_price = float(curr["Close"])
        rsi = float(curr["RSI_14"])
        sma150 = float(curr["SMA_150"])

        mentor_text = get_mentor_analysis(ticker_symbol, result, last_price, rsi, sma150)

        return (
            f"📊 *ניתוח פלייבוק: {ticker_symbol}*\n"
            f"מחיר: {last_price:.2f}$ | ממוצע 150: {sma150:.2f}$ | RSI: {rsi:.1f}\n"
            f"החלטת מנוע: *{result.get('status')}*\n\n"
            f"🎙 *דבר המנטור (מיכה):*\n"
            f"{mentor_text}"
        )
    except Exception as e:
        return f"שגיאה בניתוח {ticker_symbol}: {e}"

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(
        message,
        "אהלן! אני הבוט של מיכה סטוקס.\n"
        "אתה יכול לשלוח לי סימול של מניה (למשל: NVDA או AAPL) ואנתח אותה לפי הפלייבוק,\n"
        "או פשוט לשאול אותי כל שאלה על שיטת המסחר וניהול הסיכונים."
    )

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_text = message.text.strip()
    ticker = extract_ticker(user_text)

    bot.send_chat_action(message.chat.id, 'typing')

    if ticker and len(user_text.split()) <= 4:
        reply = analyze_and_format(ticker)
    else:
        reply = get_mentor_chat_reply(user_text)

    try:
        bot.reply_to(message, reply, parse_mode="Markdown")
    except Exception:
        bot.reply_to(message, reply)

if __name__ == "__main__":
    # הפעלת שרת הדופק בתהליכון נפרד
    threading.Thread(target=run_health_server, daemon=True).start()
    
    print("מיכה מחובר ומאזין להודעות בטלגרם...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)

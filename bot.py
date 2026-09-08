import os
import re
import time
import threading
import http.server
import socketserver
import telebot
import yfinance as yf
from supabase import create_client, Client
from engine import PlaybookEngine
from mentor import get_mentor_analysis, get_mentor_chat_reply

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN אינו מוגדר.")

bot = telebot.TeleBot(BOT_TOKEN)

# חיבור ל-Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = None

if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("[Supabase] התחברות למסד הנתונים בוצעה בהצלחה.", flush=True)
    except Exception as e:
        print(f"[Supabase Error] שגיאה בחיבור למסד הנתונים: {e}", flush=True)
else:
    print("[Supabase Warning] SUPABASE_URL או SUPABASE_KEY לא הוגדרו.", flush=True)

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
PROCESSED_MESSAGES = set()

HEBREW_TICKERS = {
    "טסלה": "TSLA",
    "אפל": "AAPL",
    "אנבידיה": "NVDA",
    "אמזון": "AMZN",
    "גוגל": "GOOGL",
    "מיקרוסופט": "MSFT",
    "מייקרוסופט": "MSFT",
    "מטא": "META",
    "מיקרון": "MU"
}

def start_health_server():
    port = int(os.environ.get("PORT", 10000))
    class QuietHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Chip is listening 24/7!")
        def log_message(self, format, *args):
            pass

    server = socketserver.TCPServer(("0.0.0.0", port), QuietHandler)
    server.allow_reuse_address = True
    print(f"[Health Server] מאזין על פורט {port}", flush=True)
    server.serve_forever()

def normalize_text(text: str) -> str:
    if not text:
        return ""
    return text.replace("’", "'").replace("`", "'").replace("״", '"')

def extract_ticker(text: str):
    clean_text = normalize_text(text)
    if BOT_USERNAME:
        clean_text = re.sub(rf"@{BOT_USERNAME}\b", "", clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r"@\w+_bot\b", "", clean_text, flags=re.IGNORECASE)

    for heb_name, ticker in HEBREW_TICKERS.items():
        if heb_name in clean_text:
            return ticker

    cashtag = re.findall(r'\$([A-Za-z]{1,5})\b', clean_text)
    if cashtag:
        return cashtag[0].upper()

    words = re.findall(r'\b[A-Za-z]{1,5}\b', clean_text.upper())
    ignored = {
        "HI", "HELLO", "OK", "BUY", "SELL", "WAIT", "BOT", "HEY", "YES", "NO", 
        "CHIP", "WHAT", "AGENT", "MARKET", "PRO", "AND", "THE", "CAN", "YOU",
        "FOR", "HOW", "WHY", "NOW", "SEE", "GET", "NEW", "TOP", "PORTFOLIO"
    }

    for word in words:
        if word not in ignored:
            return word
    return None

def get_portfolio_summary() -> str:
    if not supabase:
        return "חיבור מסד הנתונים אינו מוגדר כרגע."

    try:
        response = supabase.table("active_trades").select("*").execute()
        trades = response.data

        if not trades:
            return "💼 **תיק המסחר של צ'יפ:**\nכרגע אין עסקאות פתוחות בתיק. אנחנו סבלניים, יושבים על הגדר וממתינים לתבנית מדויקת לפי הפלייבוק!"

        lines = ["💼 **דוח תיק - פוזיציות פתוחות:**\n"]
        for trade in trades:
            ticker = trade.get("ticker")
            entry = float(trade.get("entry_price", 0))
            current = float(trade.get("current_price", entry))
            stop = float(trade.get("stop_loss", 0))
            pnl = ((current - entry) / entry) * 100 if entry > 0 else 0
            pnl_sign = "+" if pnl >= 0 else ""

            lines.append(
                f"🔹 **{ticker}**\n"
                f"  • כניסה: {entry:.2f}$ | נוכחי: {current:.2f}$ ({pnl_sign}{pnl:.2f}%)\n"
                f"  • סטופ לוס: {stop:.2f}$\n"
            )

        lines.append("🛡️ זכרו: לא מזיזים סטופים למטה לעולם. ניהול סיכונים קודם לכל.")
        return "\n".join(lines)
    except Exception as e:
        return f"שגיאה בשליפת נתוני תיק: {e}"

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
@bot.channel_post_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(
        message,
        "אהלן! אני צ'יפ 🤖📊\n"
        "הסיידקיק שלכם לניתוח טכני וסווינג לפי הפלייבוק.\n\n"
        "מה אפשר לעשות איתי?\n"
        "• שאלו אותי על מניה (למשל: 'מה עם אפל?', 'NVDA', '$TSLA')\n"
        "• בדקו מצב תיק עם הפקודה /portfolio או שאלו 'מה הטריידים הפתוחים?'\n"
        "• דברו איתי חופשי בערוץ ובקבוצה!"
    )

@bot.message_handler(commands=['portfolio'])
@bot.channel_post_handler(commands=['portfolio'])
def handle_portfolio_command(message):
    reply = get_portfolio_summary()
    bot.reply_to(message, reply)

def process_incoming_message(message):
    if getattr(message, 'is_automatic_forward', False):
        return

    msg_key = f"{message.chat.id}_{message.message_id}"
    if msg_key in PROCESSED_MESSAGES:
        return
    PROCESSED_MESSAGES.add(msg_key)
    if len(PROCESSED_MESSAGES) > 500:
        PROCESSED_MESSAGES.clear()

    raw_text = message.text or message.caption or ""
    user_text = raw_text.strip()
    if not user_text:
        return

    chat_type = message.chat.type
    chat_id = message.chat.id
    normalized = normalize_text(user_text)
    is_private = (chat_type == 'private')

    is_reply_to_bot = False
    if message.reply_to_message and message.reply_to_message.from_user:
        rep_id = message.reply_to_message.from_user.id
        rep_user = (message.reply_to_message.from_user.username or "").lower()
        if rep_id == BOT_ID or (BOT_USERNAME and rep_user == BOT_USERNAME):
            is_reply_to_bot = True

    is_mentioned = False
    if BOT_USERNAME and f"@{BOT_USERNAME}" in normalized.lower():
        is_mentioned = True
    elif any(k in normalized.lower() for k in ["צ'יפ", "ציפ", "chip"]):
        is_mentioned = True

    # בדיקה האם המשתמש שואל על התיק או הפוזיציות
    portfolio_keywords = ["פוזיציות", "תיק", "עסקאות פתוחות", "טריידים פתוחים", "portfolio"]
    is_portfolio_query = any(k in normalized.lower() for k in portfolio_keywords)

    ticker = extract_ticker(user_text)

    if not is_private and not ticker and not is_reply_to_bot and not is_mentioned and not is_portfolio_query:
        return

    try:
        bot.send_chat_action(chat_id, 'typing')
    except Exception:
        pass

    try:
        if is_portfolio_query:
            reply = get_portfolio_summary()
        elif ticker:
            reply = analyze_and_format(ticker)
        else:
            clean_text = normalized
            if BOT_USERNAME:
                clean_text = re.sub(rf"@{BOT_USERNAME}", "", clean_text, flags=re.IGNORECASE)
            clean_text = re.sub(r"\b(צ'יפ|ציפ|chip)\b", "", clean_text, flags=re.IGNORECASE).strip()
            reply = get_mentor_chat_reply(clean_text or normalized)

        bot.reply_to(message, reply)
    except Exception as e:
        print(f"[Handler Error] {e}", flush=True)

@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_text_messages(message):
    process_incoming_message(message)

@bot.channel_post_handler(func=lambda message: True, content_types=['text'])
def handle_channel_posts(message):
    process_incoming_message(message)

if __name__ == "__main__":
    t = threading.Thread(target=start_health_server, daemon=True)
    t.start()
    time.sleep(1)
    print("...צ'יפ מחובר ומאזין בטלגרם (פרטי + קבוצות + ערוצים)", flush=True)
    bot.infinity_polling(timeout=20, long_polling_timeout=15)

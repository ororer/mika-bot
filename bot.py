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
from db import get_active_trades, get_trade_history

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

def format_active_trades() -> str:
    trades = get_active_trades()
    if not trades:
        return "💼 כרגע אין עסקאות פעילות בתיק. השולחן נקי, אנחנו על הגדר ומחכים לסטאפ מנצח לפי הפלייבוק!"

    response_lines = ["💼 *סטטוס עסקאות פעילות (Chip Swing Portfolio):*\n"]
    for t in trades:
        ticker = t.get("ticker", "")
        entry_price = float(t.get("entry_price", 0))
        stop_loss = float(t.get("stop_loss", 0))
        target_price = t.get("target_price")
        target_str = f"{float(target_price):.2f}$" if target_price else "פתוח"

        # בדיקת מחיר חי דרך yfinance
        curr_price = entry_price
        pnl_pct = 0.0
        try:
            live_data = yf.Ticker(ticker).history(period="1d")
            if not live_data.empty:
                curr_price = float(live_data["Close"].iloc[-1])
                pnl_pct = ((curr_price - entry_price) / entry_price) * 100
        except Exception:
            pass

        sign = "+" if pnl_pct >= 0 else ""
        icon = "🟢" if pnl_pct >= 0 else "🔴"

        response_lines.append(
            f"{icon} *{ticker}* | מחיר נוכחי: {curr_price:.2f}$ ({sign}{pnl_pct:.2f}%)\n"
            f"   • כניסה: {entry_price:.2f}$ | סטופ: {stop_loss:.2f}$ | יעד: {target_str}\n"
            f"   • סטאפ: {t.get('setup_type', 'Breakout')} | נכנס בתאריך: {t.get('entry_date')}\n"
        )

    response_lines.append("שמרו על המשמעת, סטופ לוס בברזל! 🛡️")
    return "\n".join(response_lines)

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
        "FOR", "HOW", "WHY", "NOW", "SEE", "GET", "NEW", "TOP", "TRADES"
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

    # בדיקה ישירה לפקודת עסקאות פתוחות
    is_trades_query = any(cmd in normalized.lower() for cmd in ["/trades", "עסקאות פתוחות", "פוזיציות פתוחות", "תיק עסקאות"])

    if not is_private and not is_reply_to_bot and not is_mentioned and not is_trades_query:
        ticker = extract_ticker(user_text)
        if not ticker:
            return

    try:
        bot.send_chat_action(chat_id, 'typing')
    except Exception:
        pass

    try:
        if is_trades_query:
            reply = format_active_trades()
        else:
            ticker = extract_ticker(user_text)
            if ticker:
                reply = analyze_and_format(ticker)
            else:
                clean_text = normalized
                if BOT_USERNAME:
                    clean_text = re.sub(rf"@{BOT_USERNAME}", "", clean_text, flags=re.IGNORECASE)
                clean_text = re.sub(r"\b(צ'יפ|ציפ|chip)\b", "", clean_text, flags=re.IGNORECASE).strip()
                reply = get_mentor_chat_reply(clean_text or normalized)

        bot.reply_to(message, reply, parse_mode="Markdown")
    except Exception as e:
        print(f"[Handler Error] {e}", flush=True)

@bot.message_handler(commands=['trades'])
def handle_trades_command(message):
    process_incoming_message(message)

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

import os
import re
import time
import threading
import http.server
import socketserver
import urllib.request
import telebot
import requests
import yfinance as yf
from collections import deque
from engine import PlaybookEngine
from mentor import get_mentor_analysis, get_mentor_chat_reply
from db import get_active_trades, get_trade_history
from smart_money import format_smart_money_summary

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

PROCESSED_MESSAGES = deque(maxlen=500)
USER_LAST_TICKER = {}
USER_CHAT_HISTORY = {}
USER_LAST_INTERACTION = {}

memory_lock = threading.Lock()
MAX_MEMORY_USERS = 1000

HEBREW_TICKERS = {
    "טסלה": "TSLA",
    "אפל": "AAPL",
    "אנבידיה": "NVDA",
    "אמזון": "AMZN",
    "גוגל": "GOOGL",
    "מיקרוסופט": "MSFT",
    "מייקרוסופט": "MSFT",
    "מטא": "META",
    "מיקרון": "MU",
    "נביוס": "NBIS",
    "טראמפ": "DJT",
    "סוקסל": "SOXL",
    "ספיי": "SPY",
    "קיו": "QQQ",
    "טריפל": "TQQQ",
    "נטפליקס": "NFLX",
    "סנופי": "SPY",
    "נסדק": "QQQ",
    "נאסדק": "QQQ",
    "אקסון": "XOM",
    "אקסון מוביל": "XOM"
}

IGNORED_WORDS = {
    "HI", "HELLO", "OK", "BUY", "SELL", "WAIT", "BOT", "HEY", "YES", "NO",
    "CHIP", "WHAT", "AGENT", "MARKET", "PRO", "AND", "THE", "CAN", "YOU",
    "FOR", "HOW", "WHY", "NOW", "SEE", "GET", "NEW", "TOP", "TRADES", "AI",
    "STOP", "LOSS", "TARGET", "PRICE", "VIEW", "API", "CODE", "APP", "CHAT",
    "RUN", "USER", "TRUE", "FALSE", "NONE", "INFO", "DATA", "TEST", "RSI",
    "MACD", "EMA", "SMA", "VCP", "ATR", "RVOL", "POST", "JSON", "GET", "WIFI", "USB",
    "CEO", "FED", "VIP", "TEAM", "HOME", "PLAY", "ZOOM", "SNOW"
}

def clean_memory_leak():
    """מונע זליגת זיכרון על ידי הגבלת כמות המשתמשים הנשמרים ברקע"""
    with memory_lock:
        if len(USER_LAST_INTERACTION) > MAX_MEMORY_USERS:
            # מחיקת 100 המשתמשים הישנים ביותר כדי לפנות מקום
            sorted_users = sorted(USER_LAST_INTERACTION.items(), key=lambda x: x[1])
            for user, _ in sorted_users[:100]:
                USER_LAST_INTERACTION.pop(user, None)
                USER_CHAT_HISTORY.pop(user, None)
                USER_LAST_TICKER.pop(user, None)

def get_clean_session():
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
    })
    return session

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

    try:
        socketserver.TCPServer.allow_reuse_address = True
        server = socketserver.TCPServer(("0.0.0.0", port), QuietHandler)
        print(f"[Health Server] מאזין על פורט {port}", flush=True)
        server.serve_forever()
    except Exception as e:
        print(f"[Health Server Error] {e}", flush=True)

def keep_alive():
    app_url = os.environ.get("RENDER_EXTERNAL_URL")
    if not app_url:
        print("[Keep-Alive] אזהרה: משתנה הסביבה RENDER_EXTERNAL_URL אינו מוגדר.")
        return

    def run():
        while True:
            try:
                urllib.request.urlopen(app_url, timeout=10)
            except Exception as e:
                print(f"[Keep-Alive] Ping error: {e}", flush=True)
            time.sleep(600)
    
    threading.Thread(target=run, daemon=True).start()

def normalize_text(text: str) -> str:
    if not text:
        return ""
    return text.replace("’", "'").replace("`", "'").replace("״", '"')

def format_active_trades() -> str:
    trades = get_active_trades()
    if not trades:
        return "💼 כרגע אין עסקאות פעילות בתיק. השולחן נקי, אנחנו על הגדר ומחכים לסטאפ מנצח לפי הפלייבוק!"

    response_lines = ["💼 סטטוס עסקאות פעילות (Chip Swing Portfolio):\n"]
    session = get_clean_session()
    
    for t in trades:
        ticker = t.get("ticker", "")
        entry_price = float(t.get("entry_price", 0))
        stop_loss = float(t.get("stop_loss", 0))
        target_price = t.get("target_price")
        
        try:
            target_str = f"{float(target_price):.2f}$" if target_price else "פתוח"
        except (ValueError, TypeError):
            target_str = str(target_price) if target_price else "פתוח"

        curr_price = entry_price
        pnl_pct = 0.0
        price_status = ""
        try:
            live_data = yf.Ticker(ticker, session=session).history(period="1d")
            if not live_data.empty:
                curr_price = float(live_data["Close"].iloc[-1])
                if entry_price > 0:
                    pnl_pct = ((curr_price - entry_price) / entry_price) * 100
            
            # הגנה מפני חסימת 429 מול יאהו בסריקה המונית
            time.sleep(0.3)
        except Exception as e:
            price_status = " (מחיר היסטורי)"
            print(f"[Data Fetch Error] Live price failed for {ticker}: {e}", flush=True)

        sign = "+" if pnl_pct >= 0 else ""
        icon = "🟢" if pnl_pct >= 0 else "🔴"

        response_lines.append(
            f"{icon} {ticker} | מחיר נוכחי: {curr_price:.2f}${price_status} ({sign}{pnl_pct:.2f}%)\n"
            f"   • כניסה: {entry_price:.2f}$ | סטופ: {stop_loss:.2f}$ | יעד: {target_str}\n"
            f"   • סטאפ: {t.get('setup_type', 'Breakout')} | נכנס בתאריך: {t.get('entry_date')}\n"
        )

    response_lines.append("שמרו על המשמעת, סטופ לוס בברזל! 🛡️")
    return "\n".join(response_lines)

def extract_ticker(text: str):
    clean_text = normalize_text(text)
    if BOT_USERNAME:
        clean_text = re.sub(rf"@{BOT_USERNAME}\b", "", clean_text, flags=re.IGNORECASE)
    
    smart_tokens = ["אקמן", "קאתי", "קאת'י", "קטי", "ווד", "הואנג", "ג'נסן", "דליו", "טראמפ", "פלוסי", "ארק", "arkk"]
    if any(k in clean_text.lower() for k in smart_tokens):
        return None

    cashtags = re.findall(r'\$([A-Za-z]{1,5})\b', text)
    if cashtags:
        return cashtags[0].upper()

    for heb_name, ticker in HEBREW_TICKERS.items():
        if re.search(rf'(?<![א-ת]){heb_name}(?![א-ת])', clean_text):
            return ticker

    stock_hints = ["מניה", "מניית", "טיקר", "ניתוח", "שער", "גרף", "סווינג", "לונג", "שורט", "מחיר", "סטופ", "דעתך", "חושב", "קורה", "מצב", "בדוק"]
    has_hint = any(h in clean_text for h in stock_hints)

    uppercase_candidates = re.findall(r'\b[A-Z]{2,5}\b', text)
    valid_uppercase = [uc for uc in uppercase_candidates if uc not in IGNORED_WORDS]
    
    raw_candidates = re.findall(r'\b[A-Za-z]{1,5}\b', clean_text)
    valid_candidates = [c.upper() for c in raw_candidates if c.upper() not in IGNORED_WORDS]

    # חילוץ קפדני למניעת זיהוי מילים באנגלית כמניות בטעות
    if valid_uppercase:
        if has_hint or len(valid_candidates) == 1:
            return valid_uppercase[0]
            
    if valid_candidates:
        if has_hint or len(clean_text.split()) <= 3:
            return valid_candidates[0]

    return None

def analyze_and_format(ticker_symbol: str, user_prompt: str = "") -> str:
    try:
        session = get_clean_session()
        ticker = yf.Ticker(ticker_symbol, session=session)
        df = ticker.history(period="250d", interval="1d")

        if df.empty or len(df) < 155:
            return f"לא מצאתי מספיק נתונים עדכניים על {ticker_symbol}. ייתכן שהטיקר אינו תקין או שקיימת מגבלת רשת זמנית."

        engine = PlaybookEngine(df)
        result = engine.evaluate()
        metrics = result.get("metrics", {})

        last_price = metrics.get("close", 0.0)
        sma20 = metrics.get("sma20", 0.0)
        rsi = metrics.get("rsi", 50.0)
        sma150 = metrics.get("sma150", 0.0)
        rvol = metrics.get("rvol", 1.0)
        atr = metrics.get("atr", 0.0)

        mentor_text = get_mentor_analysis(ticker_symbol, result, metrics, user_prompt)

        formatted_reply = (
            f"📊 צ'יפ בודק את {ticker_symbol}:\n"
            f"מחיר: {last_price:.2f}$ | ממוצע 20: {sma20:.2f}$ | ממוצע 150: {sma150:.2f}$\n"
            f"RSI: {rsi:.1f} | RVOL: {rvol:.2f} | ATR: {atr:.2f}$\n"
            f"החלטת מנוע: {result.get('status')} ({result.get('setup')})\n\n"
            f"💡 דבר המנטור:\n"
            f"{mentor_text}"
        )
        return formatted_reply
    except Exception as e:
        print(f"[Analyze Error] {e}", flush=True)
        return f"שגיאה בבדיקת {ticker_symbol}. נסה שוב בעוד מספר רגעים."

def safe_reply(message, text: str):
    if not text:
        return
    chat_id = message.chat.id
    is_channel = (message.chat.type == 'channel')

    if is_channel:
        try:
            bot.send_message(chat_id, text, parse_mode="Markdown")
        except Exception:
            bot.send_message(chat_id, text)
        return

    try:
        bot.reply_to(message, text, parse_mode="Markdown")
    except Exception:
        try:
            bot.reply_to(message, text)
        except Exception as e:
            print(f"[Reply Error] {e}", flush=True)

def process_incoming_message(message):
    if getattr(message, 'is_automatic_forward', False):
        return

    msg_key = f"{message.chat.id}_{message.message_id}"
    with memory_lock:
        if msg_key in PROCESSED_MESSAGES:
            return
        PROCESSED_MESSAGES.append(msg_key)

    raw_text = message.text or message.caption or ""
    user_text = raw_text.strip()
    if not user_text:
        return

    chat_type = message.chat.type
    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else chat_id
    memory_key = f"{chat_id}_{user_id}"
    normalized = normalize_text(user_text)
    is_private = (chat_type == 'private')
    is_channel = (chat_type == 'channel')

    clean_memory_leak()

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

    is_trades_query = any(cmd in normalized.lower() for cmd in ["/trades", "עסקאות פתוחות", "פוזיציות פתוחות", "תיק עסקאות"])
    
    smart_money_triggers = [
        "/smartmoney", "/pelosi", "/ackman", "/cathie", "/jensen", "/trump",
        "פלוסי", "אקמן", "קאת'י", "קאתי", "קטי", "ווד", "ג'נסן", "גנסן", "דליו", "טראמפ", "מוסדיים", "מחזיקה", "מחזיק", "arkk"
    ]
    is_smart_money = any(cmd in normalized.lower() for cmd in smart_money_triggers)

    ticker = extract_ticker(raw_text)

    with memory_lock:
        if not ticker:
            follow_up_words = ["סטופ", "יעד", "קניתי", "קונה", "מוכר", "בפנים", "נכנסתי", "הפסד", "רווח", "ממוצע", "20", "50", "150", "200", "sma", "ema"]
            if any(w in normalized for w in follow_up_words):
                if memory_key in USER_LAST_TICKER:
                    if time.time() - USER_LAST_TICKER[memory_key]["time"] < 300:
                        ticker = USER_LAST_TICKER[memory_key]["ticker"]

        if ticker:
            USER_LAST_TICKER[memory_key] = {"ticker": ticker, "time": time.time()}

        is_ongoing_conversation = False
        if not is_channel and memory_key in USER_LAST_INTERACTION:
            if time.time() - USER_LAST_INTERACTION[memory_key] < 60:
                is_ongoing_conversation = True

    if not is_private and not is_reply_to_bot and not is_mentioned and not is_trades_query and not is_smart_money and not ticker and not is_ongoing_conversation:
        return

    print(f"[Incoming Msg] Chat: {chat_id} | Type: {chat_type} | Text: '{user_text}'", flush=True)

    try:
        bot.send_chat_action(chat_id, 'typing')
    except Exception:
        pass

    try:
        if is_trades_query:
            reply = format_active_trades()
        elif is_smart_money:
            reply = format_smart_money_summary(normalized)
        elif ticker:
            reply = analyze_and_format(ticker, user_text)
        else:
            clean_text = normalized
            if BOT_USERNAME:
                clean_text = re.sub(rf"@{BOT_USERNAME}\b", "", clean_text, flags=re.IGNORECASE)
            clean_text = re.sub(r"\b(chip|CHIP)\b", "", clean_text, flags=re.IGNORECASE)
            clean_text = re.sub(r"(?<![א-ת])(צ'יפ|ציפ)(?![א-ת])", "", clean_text)
            clean_text = clean_text.strip()

            prompt_text = clean_text if clean_text else normalized
            
            with memory_lock:
                if memory_key not in USER_CHAT_HISTORY:
                    USER_CHAT_HISTORY[memory_key] = []
                chat_history = list(USER_CHAT_HISTORY[memory_key])
                
            reply = get_mentor_chat_reply(prompt_text, chat_history)

        with memory_lock:
            if memory_key not in USER_CHAT_HISTORY:
                USER_CHAT_HISTORY[memory_key] = []
            
            USER_CHAT_HISTORY[memory_key].append({"role": "user", "text": user_text})
            USER_CHAT_HISTORY[memory_key].append({"role": "model", "text": reply})
            
            if len(USER_CHAT_HISTORY[memory_key]) > 10:
                USER_CHAT_HISTORY[memory_key] = USER_CHAT_HISTORY[memory_key][-10:]
            
            USER_LAST_INTERACTION[memory_key] = time.time()

        safe_reply(message, reply)
    except Exception as e:
        print(f"[Handler Error] {e}", flush=True)

@bot.message_handler(commands=['trades', 'pelosi', 'smartmoney', 'ackman', 'cathie', 'jensen', 'trump'])
def handle_commands(message):
    process_incoming_message(message)

@bot.message_handler(func=lambda message: True, content_types=['text', 'photo', 'document'])
def handle_all_messages(message):
    process_incoming_message(message)

@bot.channel_post_handler(func=lambda message: True, content_types=['text', 'photo', 'document'])
def handle_channel_posts(message):
    process_incoming_message(message)

if __name__ == "__main__":
    t = threading.Thread(target=start_health_server, daemon=True)
    t.start()
    
    keep_alive()
    
    try:
        bot.remove_webhook()
    except Exception:
        pass
    time.sleep(2)

    print("...צ'יפ מחובר ומאזין בטלגרם (פרטי + קבוצות + ערוצים)", flush=True)
    
    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=15)
        except telebot.apihelper.ApiTelegramException as e:
            if "409" in str(e):
                time.sleep(5)
            else:
                time.sleep(2)
        except Exception as ex:
            print(f"[Polling Error] {ex}", flush=True)
            time.sleep(3)

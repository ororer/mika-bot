import os
import re
import time
import threading
import http.server
import socketserver
import urllib.request
import telebot
import yfinance as yf
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

PROCESSED_MESSAGES = set()
USER_LAST_TICKER = {}

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
    "נאסדק": "QQQ"
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

def keep_alive():
    """שעון מעורר פנימי שפונה לשרת של עצמו כל 10 דקות כדי למנוע הירדמות ב-Render"""
    def run():
        while True:
            try:
                urllib.request.urlopen("https://mika-bot-folt.onrender.com")
            except Exception:
                pass
            time.sleep(600)  # ממתין 10 דקות (600 שניות) לפני הפינג הבא
    
    threading.Thread(target=run, daemon=True).start()
    print("[Keep-Alive] שעון מעורר פנימי הופעל בהצלחה", flush=True)

def normalize_text(text: str) -> str:
    if not text:
        return ""
    return text.replace("’", "'").replace("`", "'").replace("״", '"')

def format_active_trades() -> str:
    trades = get_active_trades()
    if not trades:
        return "💼 כרגע אין עסקאות פעילות בתיק. השולחן נקי, אנחנו על הגדר ומחכים לסטאפ מנצח לפי הפלייבוק!"

    response_lines = ["💼 סטטוס עסקאות פעילות (Chip Swing Portfolio):\n"]
    for t in trades:
        ticker = t.get("ticker", "")
        entry_price = float(t.get("entry_price", 0))
        stop_loss = float(t.get("stop_loss", 0))
        target_price = t.get("target_price")
        target_str = f"{float(target_price):.2f}$" if target_price else "פתוח"

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
            f"{icon} {ticker} | מחיר נוכחי: {curr_price:.2f}$ ({sign}{pnl_pct:.2f}%)\n"
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

    smart_tokens = ["אקמן", "קאתי", "קאת'י", "קטי", "ווד", "הואנג", "ג'נסן", "דליו", "טראמפ", "פלוסי", "ארק", "arkk"]
    if any(k in clean_text.lower() for k in smart_tokens):
        return None

    cashtags = re.findall(r'\$([A-Za-z]{1,5})\b', clean_text)
    if cashtags:
        return cashtags[0].upper()

    chat_phrases = [
        "מה קורה", "מה נשמע", "מה המצב", "מה הולך", "היי", "שלום", "בוקר טוב",
        "ערב טוב", "איך אתה", "מי אתה", "אתה כאן", "מה צפוי", "תודה", "מה אתה חושב",
        "מה דעתך", "איך לפעול", "מה לעשות"
    ]
    if any(p in clean_text for p in chat_phrases):
        return None

    for heb_name, ticker in HEBREW_TICKERS.items():
        if heb_name in clean_text:
            return ticker

    words = re.findall(r'\b[A-Za-z]{1,5}\b', clean_text.upper())
    ignored = {
        "HI", "HELLO", "OK", "BUY", "SELL", "WAIT", "BOT", "HEY", "YES", "NO", 
        "CHIP", "WHAT", "AGENT", "MARKET", "PRO", "AND", "THE", "CAN", "YOU",
        "FOR", "HOW", "WHY", "NOW", "SEE", "GET", "NEW", "TOP", "TRADES"
    }
    filtered = [w for w in words if w not in ignored]
    if len(filtered) == 1 and len(clean_text.split()) <= 3:
        return filtered[0]

    return None

def analyze_and_format(ticker_symbol: str, user_prompt: str = "") -> str:
    try:
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period="250d", interval="1d")

        if df.empty or len(df) < 155:
            return f"לא מצאתי מספיק נתונים על {ticker_symbol}. תוודא שזה טיקר תקין."

        engine = PlaybookEngine(df)
        result = engine.evaluate()
        metrics = result.get("metrics", {})

        last_price = metrics.get("close", 0.0)
        rsi = metrics.get("rsi", 50.0)
        sma150 = metrics.get("sma150", 0.0)
        rvol = metrics.get("rvol", 1.0)
        atr = metrics.get("atr", 0.0)

        mentor_text = get_mentor_analysis(ticker_symbol, result, metrics, user_prompt)

        formatted_reply = (
            f"📊 צ'יפ בודק את {ticker_symbol}:\n"
            f"מחיר: {last_price:.2f}$ | ממוצע 150: {sma150:.2f}$ | RSI: {rsi:.1f}\n"
            f"RVOL: {rvol:.2f} | ATR: {atr:.2f}$\n"
            f"החלטת מנוע: {result.get('status')} ({result.get('setup')})\n\n"
            f"💡 דבר המנטור:\n"
            f"{mentor_text}"
        )
        return formatted_reply
    except Exception as e:
        print(f"[Analyze Error] {e}", flush=True)
        return f"שגיאה בבדיקת {ticker_symbol}."

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
    user_id = message.from_user.id if message.from_user else chat_id
    memory_key = f"{chat_id}_{user_id}"
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

    is_trades_query = any(cmd in normalized.lower() for cmd in ["/trades", "עסקאות פתוחות", "פוזיציות פתוחות", "תיק עסקאות"])
    
    smart_money_triggers = [
        "/smartmoney", "/pelosi", "/ackman", "/cathie", "/jensen", "/trump",
        "פלוסי", "אקמן", "קאת'י", "קאתי", "קטי", "ווד", "ג'נסן", "גנסן", "דליו", "טראמפ", "מוסדיים", "מחזיקה", "מחזיק", "arkk"
    ]
    is_smart_money = any(cmd in normalized.lower() for cmd in smart_money_triggers)

    ticker = extract_ticker(user_text)
    
    # מנגנון הזיכרון לשאלות המשך ללא טיקר
    if not ticker:
        follow_up_words = ["סטופ", "יעד", "קניתי", "קונה", "מוכר", "בפנים", "נכנסתי", "הפסד", "רווח"]
        if any(w in normalized for w in follow_up_words):
            if memory_key in USER_LAST_TICKER:
                if time.time() - USER_LAST_TICKER[memory_key]["time"] < 300:
                    ticker = USER_LAST_TICKER[memory_key]["ticker"]
                    print(f"[Memory] שאלת המשך זוהתה, משתמש בטיקר {ticker}", flush=True)

    if ticker:
        USER_LAST_TICKER[memory_key] = {"ticker": ticker, "time": time.time()}

    if not is_private and not is_reply_to_bot and not is_mentioned and not is_trades_query and not is_smart_money and not ticker:
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
                clean_text = clean_text.replace(f"@{BOT_USERNAME}", "")
            for tag in ["צ'יפ", "ציפ", "chip", "CHIP"]:
                clean_text = clean_text.replace(tag, "")
            clean_text = clean_text.strip()

            prompt_text = clean_text if clean_text else normalized
            reply = get_mentor_chat_reply(prompt_text)

        safe_reply(message, reply)
    except Exception as e:
        print(f"[Handler Error] {e}", flush=True)

@bot.message_handler(commands=['trades', 'pelosi', 'smartmoney', 'ackman', 'cathie', 'jensen', 'trump'])
def handle_commands(message):
    process_incoming_message(message)

@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_text_messages(message):
    process_incoming_message(message)

@bot.channel_post_handler(func=lambda message: True, content_types=['text'])
def handle_channel_posts(message):
    process_incoming_message(message)

if __name__ == "__main__":
    # הפעלת שרת הבריאות של Render
    t = threading.Thread(target=start_health_server, daemon=True)
    t.start()
    
    # הפעלת מנגנון השעון המעורר הפנימי
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

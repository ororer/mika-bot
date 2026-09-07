import os
import sys
import requests
import yfinance as yf
from engine import PlaybookEngine
from mentor import get_mentor_analysis

def send_telegram_message(text: str):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        print("[אזהרה] משתני טלגרם אינם מוגדרים.")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    
    response = requests.post(url, json=payload)
    if response.status_code != 200:
        # ניסיון שליחה ללא Markdown במקרה של תווים מיוחדים
        payload.pop("parse_mode", None)
        response = requests.post(url, json=payload)

    if response.status_code == 200:
        print("ההודעה שוגרה בהצלחה לטלגרם!")
    else:
        print(f"שגיאה מטלגרם: {response.status_code} - {response.text}")

def analyze_ticker(ticker_symbol: str):
    print(f"--- מושך נתונים עבור {ticker_symbol} ---")
    ticker = yf.Ticker(ticker_symbol)
    df = ticker.history(period="1y", interval="1d")

    if df.empty or len(df) < 155:
        print("אין מספיק נתונים לחישוב ממוצע 150.")
        return

    # הרצת מנוע החישוב של הפלייבוק
    engine = PlaybookEngine(df)
    result = engine.evaluate()

    curr = engine.df.iloc[-1]
    last_price = float(curr["Close"])
    rsi = float(curr["RSI_14"])
    sma150 = float(curr["SMA_150"])

    print("מבקש ניתוח מ-Gemini...")
    mentor_text = get_mentor_analysis(ticker_symbol, result, last_price, rsi, sma150)

    # הרכבת ההודעה
    msg = (
        f"📊 ניתוח פלייבוק: {ticker_symbol}\n"
        f"מחיר נוכחי: {last_price:.2f}$\n"
        f"ממוצע 150: {sma150:.2f}$ | RSI: {rsi:.1f}\n"
        f"החלטת מנוע: {result.get('status')}\n\n"
        f"🎙 דבר המנטור:\n"
        f"{mentor_text}"
    )

    print("שולח לטלגרם...")
    send_telegram_message(msg)

if __name__ == "__main__":
    symbol = "AAPL"
    if len(sys.argv) > 1:
        symbol = sys.argv[1].upper()
    analyze_ticker(symbol)

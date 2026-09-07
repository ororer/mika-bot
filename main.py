import sys
import yfinance as yf
from engine import PlaybookEngine
from mentor import get_mentor_analysis

def analyze_ticker(ticker_symbol: str):
    print(f"--- מושך נתונים ומנתח את {ticker_symbol} ---")
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
        print("[אזהרה] TELEGRAM_BOT_TOKEN או TELEGRAM_CHAT_ID אינם מוגדרים.")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    # ניסיון ראשון: שליחה עם עיצוב Markdown
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    
    response = requests.post(url, json=payload)
    
    # אם נכשל בגלל תווי עיצוב של Markdown, נשלח כטקסט רגיל כדי להבטיח הגעה
    if response.status_code != 200:
        payload.pop("parse_mode")
        response = requests.post(url, json=payload)
        
    if response.status_code == 200:
        print("הודעה נשלחה בהצלחה לטלגרם!")
    else:
        print(f"שגיאה בשליחת הודעה לטלגרם: {response.text}")

def analyze_ticker(ticker_symbol: str):
    print(f"--- מושך נתונים ומנתח את {ticker_symbol} ---")
    
    ticker = yf.Ticker(ticker_symbol)
    df = ticker.history(period="1y", interval="1d")

    if df.empty or len(df) < 155:
        print("שגיאה: אין מספיק נתונים היסטוריים לחישוב ממוצע 150.")
        return

    # הרצת המנוע הטכני
    engine = PlaybookEngine(df)
    result = engine.evaluate()

    # שליפת נתונים עדכניים
    curr = engine.df.iloc[-1]
    last_price = float(curr["Close"])
    rsi = float(curr["RSI_14"])
    sma150 = float(curr["SMA_150"])

    print("\nמריץ את הניתוח של מיכה (Gemini)...")
    mentor_response = get_mentor_analysis(ticker_symbol, result, last_price, rsi, sma150)
    
    # בניית ההודעה לטלגרם
    telegram_text = (
        f"📊 *ניתוח פלייבוק: {ticker_symbol}*\n"
        f"מחיר נוכחי: {last_price:.2f}$\n"
        f"ממוצע 150: {sma150:.2f}$ | RSI: {rsi:.1f}\n"
        f"החלטת מנוע: *{result['status']}*\n\n"
        f"🎙 *דבר המנטור (מיכה):*\n"
        f"{mentor_response}"
    )

    print("\nשולח לטלגרם...")
    send_telegram_message(telegram_text)

if __name__ == "__main__":
    symbol = "AAPL"
    if len(sys.argv) > 1:
        symbol = sys.argv[1].upper()
    analyze_ticker(symbol)

    ticker = yf.Ticker(ticker_symbol)
    df = ticker.history(period="1y", interval="1d")

    if df.empty or len(df) < 155:
        print("שגיאה: אין מספיק נתונים היסטוריים לחישוב ממוצע 150.")
        return

    # הרצת המנוע הטכני
    engine = PlaybookEngine(df)
    result = engine.evaluate()

    # שליפת הנתונים האחרונים עבור המנטור
    curr = engine.df.iloc[-1]
    last_price = float(curr["Close"])
    rsi = float(curr["RSI_14"])
    sma150 = float(curr["SMA_150"])

    print("\n=== החלטת המנוע הטכני ===")
    print(f"סטטוס: {result['status']}")
    print(f"הסבר: {result['message']}")

    print("\n=== הניתוח של מיכה (Gemini) ===")
    mentor_response = get_mentor_analysis(ticker_symbol, result, last_price, rsi, sma150)
    print(mentor_response)

if __name__ == "__main__":
    symbol = "AAPL"
    if len(sys.argv) > 1:
        symbol = sys.argv[1].upper()
    analyze_ticker(symbol)

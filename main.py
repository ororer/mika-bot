import sys
import yfinance as yf
from engine import PlaybookEngine

def analyze_ticker(ticker_symbol: str):
    print(f"--- מנתח את {ticker_symbol} לפי הפלייבוק ---")
    
    # הורדת נתוני נרות יומיים לשנה האחרונה
    ticker = yf.Ticker(ticker_symbol)
    df = ticker.history(period="1y", interval="1d")

    if df.empty or len(df) < 155:
        print("שגיאה: אין מספיק נתונים היסטוריים לחישוב ממוצע 150.")
        return

    # הרצת המנוע שבנינו
    engine = PlaybookEngine(df)
    result = engine.evaluate()

    # הדפסת התוצאה
    print(f"סטטוס: {result['status']}")
    print(f"הסבר: {result['message']}")
    if result.get("setup"):
        print(f"תבנית שזוהתה: {result['setup']}")
        print(f"סטופ-לוס מוגדר: {result['stop_loss']}$")

if __name__ == "__main__":
    # בדיקה על מניית ברירת מחדל (למשל AAPL)
    symbol = "AAPL"
    if len(sys.argv) > 1:
        symbol = sys.argv[1].upper()
    analyze_ticker(symbol)

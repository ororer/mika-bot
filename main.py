import sys
import yfinance as yf
from engine import PlaybookEngine
from mentor import get_mentor_analysis

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

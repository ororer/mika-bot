import yfinance as yf
import pandas as pd

def fetch_insider_trades(ticker_symbol: str = "NVDA", limit: int = 4) -> list:
    """
    מושך עסקאות בעלי עניין (Insiders) ישירות דרך yfinance שכבר מותקן במערכת.
    ללא מפתח API וללא תלות באתרים חיצוניים.
    """
    trades = []
    try:
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.insider_transactions
        
        if df is None or df.empty:
            return []

        # לקיחת העסקאות האחרונות
        recent = df.head(limit)
        
        for idx, row in recent.iterrows():
            insider = str(row.get("Insider", "בעל עניין"))
            relation = str(row.get("Position", "בכיר בחברה"))
            shares = row.get("Shares", 0)
            value = row.get("Value", 0)
            text = str(row.get("Text", ""))
            start_date = str(row.get("Start Date", ""))[:10]
            
            # סיווג סוג העסקה
            is_sale = "Sale" in text or (isinstance(shares, (int, float)) and shares < 0)
            tx_type = "🔴 מכירה (Sale)" if is_sale else "🟢 קנייה (Buy/Grant)"
            
            val_str = f"{abs(int(value)):,}$" if pd.notna(value) and value != 0 else "לא צוין"
            shares_str = f"{abs(int(shares)):,}" if pd.notna(shares) and shares != 0 else "לא צוין"

            trades.append({
                "ticker": ticker_symbol.upper(),
                "insider": insider,
                "position": relation,
                "date": start_date,
                "type": tx_type,
                "shares": shares_str,
                "value": val_str,
                "description": text
            })

        return trades
    except Exception as e:
        print(f"[SmartMoney yfinance Error] {e}", flush=True)
        return []

if __name__ == "__main__":
    res = fetch_insider_trades("NVDA", limit=3)
    print("תוצאה:", res)

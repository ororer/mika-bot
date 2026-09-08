import requests
from datetime import datetime

HOUSE_WATCHER_API = "https://house-stock-watcher-data.s3-us-west-2.amazonaws.com/data/all_transactions.json"

def fetch_recent_congress_trades(target_representative: str = "Nancy Pelosi", limit: int = 5) -> list:
    """
    מושך עסקאות אחרונות של חבר קונגרס ספציפי (ברירת מחדל: ננסי פלוסי).
    מחזיר רשימה של מילונים עם פרטי העסקה הרלוונטיים.
    """
    trades = []
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(HOUSE_WATCHER_API, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"[SmartMoney] שגיאה במשיכת נתונים: קוד סטטוס {response.status_code}")
            return []

        data = response.json()
        
        for item in data:
            rep_name = item.get("representative", "")
            # בדיקה האם העסקה שייכת לדמות המבוקשת
            if target_representative.lower() in rep_name.lower():
                ticker = item.get("ticker", "").strip().replace("--", "")
                if not ticker:
                    continue

                trade_info = {
                    "representative": rep_name,
                    "ticker": ticker.upper(),
                    "transaction_date": item.get("transaction_date"),
                    "disclosure_date": item.get("disclosure_date"),
                    "type": item.get("type", "Unknown"),  # purchase / sale_full / sale_partial
                    "amount": item.get("amount", "לא צוין"),
                    "asset_description": item.get("asset_description", "")
                }
                trades.append(trade_info)

                if len(trades) >= limit:
                    break

        return trades

    except Exception as e:
        print(f"[SmartMoney] חריגה במשיכת עסקאות קונגרס: {e}")
        return []

if __name__ == "__main__":
    print("בודק משיכת עסקאות עבור ננסי פלוסי...")
    results = fetch_recent_congress_trades("Nancy Pelosi", limit=3)
    if results:
        for r in results:
            print(f"- תאריך דיווח: {r['disclosure_date']} | טיקר: {r['ticker']} | סוג: {r['type']} | סכום: {r['amount']}")
    else:
        print("לא נמצאו עסקאות או שהייתה שגיאת רשת.")

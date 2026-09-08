import requests
from datetime import datetime

def fetch_recent_congress_trades(target_representative: str = "Nancy Pelosi", limit: int = 5) -> list:
    """
    מושך עסקאות אחרונות של ננסי פלוסי מחברי הקונגרס.
    """
    trades = []
    # מקור API מהיר של עסקאות פלוסי המעודכן ישירות מדיווחי ה-STOCK Act
    url = "https://raw.githubusercontent.com/swar/pelosi-stock-tracker/master/data/trades.json"
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        res = requests.get(url, headers=headers, timeout=10)
        
        if res.status_code == 200:
            data = res.json()
            # מיון לפי תאריך יורד
            sorted_data = sorted(data, key=lambda x: x.get("disclosure_date", ""), reverse=True)
            for item in sorted_data[:limit]:
                ticker = item.get("ticker", "").strip()
                if not ticker:
                    continue
                trades.append({
                    "representative": "Nancy Pelosi",
                    "ticker": ticker.upper(),
                    "transaction_date": item.get("transaction_date", "לא ידוע"),
                    "disclosure_date": item.get("disclosure_date", "לא ידוע"),
                    "type": item.get("type", "עסקה"),
                    "amount": item.get("amount", "לא צוין"),
                    "asset_description": item.get("description", "")
                })
            return trades

    except Exception as e:
        print(f"[SmartMoney] Primary source failed: {e}", flush=True)

    # מקור גיבוי מהיר
    try:
        backup_url = "https://house-stock-watcher-data.s3-us-west-2.amazonaws.com/data/all_transactions.json"
        res = requests.get(backup_url, headers={"User-Agent": "MarketAgentBot/1.0"}, timeout=12)
        if res.status_code == 200:
            data = res.json()
            for item in data:
                rep = item.get("representative", "")
                if "pelosi" in rep.lower():
                    ticker = item.get("ticker", "").strip().replace("--", "")
                    if ticker:
                        trades.append({
                            "representative": rep,
                            "ticker": ticker.upper(),
                            "transaction_date": item.get("transaction_date", ""),
                            "disclosure_date": item.get("disclosure_date", ""),
                            "type": item.get("type", "Unknown"),
                            "amount": item.get("amount", "לא צוין"),
                            "asset_description": item.get("asset_description", "")
                        })
                        if len(trades) >= limit:
                            break
            return trades
    except Exception as e2:
        print(f"[SmartMoney] Backup source failed: {e2}", flush=True)

    return []

if __name__ == "__main__":
    results = fetch_recent_congress_trades("Nancy Pelosi", limit=3)
    print("תוצאות:", results)

import requests

def fetch_recent_congress_trades(target_representative: str = "Nancy Pelosi", limit: int = 5) -> list:
    """
    מושך עסקאות קונגרס עדכניות ישירות מה-API הרשמי הפתוח.
    """
    trades = []
    
    # 1. מקור רשמי ראשי: House Stock Watcher API הפתוח (שאינו דורש הרשאות S3)
    url = "https://house-stock-watcher-data.azurewebsites.net/api/v1/data"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    print(f"[SmartMoney] מתחבר למקור נתונים: {url}...", flush=True)

    try:
        response = requests.get(url, headers=headers, timeout=15)
        print(f"[SmartMoney] סטטוס תגובה: {response.status_code}", flush=True)
        
        if response.status_code == 200:
            data = response.json()
            for item in data:
                rep_name = item.get("representative", "")
                if "pelosi" in rep_name.lower():
                    ticker = item.get("ticker", "").strip().replace("--", "")
                    if not ticker or ticker == "N/A":
                        continue

                    tx_type = item.get("type", "עסקה")
                    if tx_type == "purchase":
                        tx_type_str = "🟢 קנייה (Buy)"
                    elif "sale" in tx_type:
                        tx_type_str = "🔴 מכירה (Sell)"
                    else:
                        tx_type_str = tx_type

                    trades.append({
                        "representative": rep_name,
                        "ticker": ticker.upper(),
                        "transaction_date": item.get("transaction_date", "לא ידוע"),
                        "disclosure_date": item.get("disclosure_date", "לא ידוע"),
                        "type": tx_type_str,
                        "amount": item.get("amount", "לא צוין"),
                        "asset_description": item.get("asset_description", "")
                    })

                    if len(trades) >= limit:
                        break

            if trades:
                print(f"[SmartMoney] נמצאו בהצלחה {len(trades)} עסקאות עבור פלוסי", flush=True)
                return trades
    except Exception as e:
        print(f"[SmartMoney Source 1 Error]: {e}", flush=True)

    # 2. מקור גיבוי: Capitol Trades API
    try:
        backup_url = "https://spider.capitoltrades.com/trades?page=1&pageSize=50"
        backup_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json"
        }
        res = requests.get(backup_url, headers=backup_headers, timeout=12)
        if res.status_code == 200:
            items = res.json().get("data", [])
            for item in items:
                pol = item.get("politician", {})
                full_name = f"{pol.get('firstName', '')} {pol.get('lastName', '')}".strip()
                if "pelosi" in full_name.lower():
                    asset = item.get("asset", {})
                    ticker = asset.get("assetTicker", "")
                    if not ticker:
                        continue
                    
                    tx_type = item.get("txType", "עסקה")
                    type_str = "🟢 קנייה (Buy)" if tx_type == "buy" else ("🔴 מכירה (Sell)" if "sell" in tx_type else tx_type)
                    
                    trades.append({
                        "representative": "Nancy Pelosi",
                        "ticker": ticker.upper(),
                        "transaction_date": item.get("txDate", "לא ידוע")[:10],
                        "disclosure_date": item.get("pubDate", "לא ידוע")[:10],
                        "type": type_str,
                        "amount": f"{item.get('value', 0):,}$" if item.get('value') else "לא צוין",
                        "asset_description": asset.get("assetName", "")
                    })
                    if len(trades) >= limit:
                        break
            if trades:
                return trades
    except Exception as e2:
        print(f"[SmartMoney Source 2 Error]: {e2}", flush=True)

    return trades

if __name__ == "__main__":
    res = fetch_recent_congress_trades("Nancy Pelosi", limit=3)
    print("תוצאות:", res)

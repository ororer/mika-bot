import requests
import json

def fetch_recent_congress_trades(target_representative: str = "Nancy Pelosi", limit: int = 5) -> list:
    """
    מושך עסקאות מדווחות של חברי קונגרס עם לוגים מפורשים למניעת ניחושים.
    """
    trades = []
    
    # מקור 1: House Stock Watcher - שליפת נתוני סיכום אחרונים (הקובץ הקל והמעודכן)
    # נתיב ה-transactions הרשמי המעודכן
    url = "https://house-stock-watcher-data.s3-us-west-2.amazonaws.com/data/all_transactions.json"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    print(f"[SmartMoney Debug] מתחיל משיכה עבור {target_representative} מ-{url}...", flush=True)

    try:
        # הגדלת timeout ל-25 שניות כדי לאפשר הורדה מלאה לשרת
        response = requests.get(url, headers=headers, timeout=25)
        print(f"[SmartMoney Debug] קוד תגובה HTTP: {response.status_code}", flush=True)
        
        if response.status_code == 200:
            data = response.json()
            print(f"[SmartMoney Debug] סך כל העסקאות שנטענו בקובץ: {len(data)}", flush=True)
            
            for item in data:
                rep_name = item.get("representative", "")
                if "pelosi" in rep_name.lower():
                    ticker = item.get("ticker", "").strip().replace("--", "")
                    if not ticker:
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

            print(f"[SmartMoney Debug] נמצאו {len(trades)} עסקאות עבור פלוסי", flush=True)
            return trades
        else:
            print(f"[SmartMoney Debug] שגיאת שרת מרוחק: {response.status_code} - {response.text[:100]}", flush=True)

    except requests.exceptions.Timeout:
        print("[SmartMoney Debug] שגיאה: Timeout - ההורדה לקחה יותר מ-25 שניות ב-Render", flush=True)
    except Exception as e:
        print(f"[SmartMoney Debug] חריגה כללית במשיכה: {type(e).__name__} - {e}", flush=True)

    return trades

if __name__ == "__main__":
    t = fetch_recent_congress_trades("Nancy Pelosi", limit=3)
    print("תוצאה מקומית:", t)

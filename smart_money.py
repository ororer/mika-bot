import yfinance as yf
import pandas as pd

# מיפוי דמויות מפתח לטיקרים ולקרנות העיקריות שלהם
INSIDERS_DIRECTORY = {
    "ackman": {
        "name": "ביל אקמן (Pershing Square)",
        "ticker": "CMG", # פוזיציית עוגן מרכזית / אפשר גם HLT או GOOGL
        "etf_or_fund": "PSH.AS",
        "description": "קרן Pershing Square מתמקדת במספר מצומצם של חברות איכותיות עם חפיר תחרותי עמוק."
    },
    "cathie": {
        "name": "קאת'י ווד (ARK Invest)",
        "ticker": "ARKK",
        "etf_or_fund": "ARKK",
        "description": "השקעות בצמיחה משבשת, בינה מלאכותית, רובוטיקה ובלוקצ'יין."
    },
    "jensen": {
        "name": "ג'נסן הואנג (NVIDIA CEO)",
        "ticker": "NVDA",
        "etf_or_fund": None,
        "description": "מנכ\"ל ומייסד אנבידיה - דיווחי מסחר ומימושים שגרתיים (Form 4)."
    },
    "dalio": {
        "name": "ריי דליו (Bridgewater)",
        "ticker": "SPY",
        "etf_or_fund": "SPY",
        "description": "אסטרטגיית All-Weather מאקרו, פיזור רחב והגנה מפני אינפלציה ותנודתיות."
    },
    "trump": {
        "name": "דונלד טראמפ (DJT Media)",
        "ticker": "DJT",
        "etf_or_fund": None,
        "description": "תנודתיות מבוססת סנטימנט פוליטי ומומנטום ברשתות החברתיות."
    },
    "pelosi": {
        "name": "ננסי פלוסי (חברת קונגרס)",
        "ticker": "NVDA",
        "etf_or_fund": None,
        "description": "מעקב עסקאות טכנולוגיה ואופציות Call עמוקות בתוך הכסף."
    }
}

def get_insider_key(text: str) -> str:
    """
    מזהה מתוך טקסט הודעה לאיזו דמות הכוונה.
    """
    t = text.lower()
    if any(k in t for k in ["אקמן", "ackman", "פרשינג"]):
        return "ackman"
    if any(k in t for k in ["קאת'י", "קאתי", "cathie", "wood", "ארק", "arkk"]):
        return "cathie"
    if any(k in t for k in ["ג'נסן", "גנסן", "הואנג", "jensen", "huang"]):
        return "jensen"
    if any(k in t for k in ["דליו", "dalio", "ברידג'ווטר", "ברידגוור"]):
        return "dalio"
    if any(k in t for k in ["טראמפ", "trump", "djt"]):
        return "trump"
    if any(k in t for k in ["פלוסי", "pelosi"]):
        return "pelosi"
    return "jensen" # ברירת מחדל אם נשאל כללי

def fetch_insider_trades(ticker_symbol: str, limit: int = 4) -> list:
    """
    מושך עסקאות בעלי עניין ישירות מ-yfinance.
    """
    trades = []
    try:
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.insider_transactions
        
        if df is None or df.empty:
            return []

        recent = df.head(limit)
        for _, row in recent.iterrows():
            insider = str(row.get("Insider", "בעל עניין"))
            relation = str(row.get("Position", "בכיר"))
            shares = row.get("Shares", 0)
            value = row.get("Value", 0)
            text = str(row.get("Text", ""))
            start_date = str(row.get("Start Date", ""))[:10]

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
                "value": val_str
            })
        return trades
    except Exception as e:
        print(f"[SmartMoney Error] {e}", flush=True)
        return []

def format_smart_money_summary(query_text: str = "") -> str:
    """
    מייצר דוח מסכם על דמות המפתח שנבחרה.
    """
    key = get_insider_key(query_text)
    profile = INSIDERS_DIRECTORY.get(key, INSIDERS_DIRECTORY["jensen"])
    target_ticker = profile["ticker"]
    
    trades = fetch_insider_trades(target_ticker, limit=3)
    
    # שליפת נתוני מחיר נוכחיים של הנכס
    curr_price_str = ""
    try:
        hist = yf.Ticker(target_ticker).history(period="2d")
        if not hist.empty:
            price = hist["Close"].iloc[-1]
            curr_price_str = f" | מחיר שוק: {price:.2f}$"
    except Exception:
        pass

    lines = [
        f"🏛️ **מעקב Smart Money & Insiders:**",
        f"👤 **דמות:** {profile['name']}",
        f"🎯 **נכס במעקב:** {target_ticker}{curr_price_str}",
        f"ℹ️ {profile['description']}\n"
    ]

    if trades:
        lines.append("📋 **פעולות ודיווחים רשמיים אחרונים בנכס:**")
        for t in trades:
            lines.append(
                f"• {t['insider']} ({t['position']})\n"
                f"  פעולה: {t['type']} | כמות: {t['shares']} מניות | שווי: {t['value']}\n"
                f"  תאריך דיווח: {t['date']}"
            )
    else:
        lines.append(f"לא נרשמו תנועות בעלי עניין חריגות לאחרונה ב-{target_ticker}. הטיקר יציב.")

    lines.append("\n💡 **דבר המנטור:** מעקב מוסדיים נותן כיוון רוח, אבל טריגר כניסה לסווינג נלקח רק על פי הפלייבוק (ממוצע 150 + דחיסת תנודתיות)!")
    return "\n".join(lines)

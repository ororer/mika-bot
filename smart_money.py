import yfinance as yf
import pandas as pd

INSIDERS_DIRECTORY = {
    "ackman": {
        "name": "ביל אקמן (Pershing Square)",
        "ticker": "PSHZF",
        "type": "fund",
        "core_holdings": [
            "Alphabet (GOOGL)",
            "Chipotle Mexican Grill (CMG)",
            "Hilton Worldwide (HLT)",
            "Restaurant Brands (QSR)",
            "Howard Hughes Holdings (HHH)"
        ],
        "description": "קרן Pershing Square מתמקדת בריכוז גבוה של חברות ענק איכותיות עם מודל עסקי צפוי וחפיר תחרותי עמוק."
    },
    "cathie": {
        "name": "קאת'י ווד (ARK Invest)",
        "ticker": "ARKK",
        "type": "etf",
        "core_holdings": [
            "Tesla (TSLA)",
            "Roku (ROKU)",
            "Coinbase (COIN)",
            "Block (SQ)",
            "Roblox (RBLX)"
        ],
        "description": "קרן החדשנות ARKK משקיעה בחברות צמיחה משבשת, בינה מלאכותית, בלוקצ'יין ורובוטיקה."
    },
    "jensen": {
        "name": "ג'נסן הואנג (מנכ\"ל NVIDIA)",
        "ticker": "NVDA",
        "type": "insider",
        "core_holdings": [
            "מניות שליטה והנהלה ב-NVIDIA (NVDA)"
        ],
        "description": "מעקב אחר דיווחי Form 4 ומימושי מניות תקופתיים (תוכנית 10b5-1 עיוורת)."
    },
    "dalio": {
        "name": "ריי דליו (Bridgewater Associates)",
        "ticker": "SPY",
        "type": "fund",
        "core_holdings": [
            "מדד S&P 500 (SPY / IVV)",
            "שווקים מתעוררים (IEMG)",
            "קרן סחורות וזהב (GLD)",
            "אג\"ח ממשלת ארה\"ב לטווח ארוך (TLT)"
        ],
        "description": "אסטרטגיית All-Weather מאקרו: פיזור גלובלי והגנה מתנודתיות מחזורי חוב ואינפלציה."
    },
    "trump": {
        "name": "דונלד טראמפ (תיק נכסים וגילוי פיננסי)",
        "ticker": "DJT",
        "type": "fund",
        "core_holdings": [
            "Trump Media & Technology Group ($DJT) - אחזקת שליטה",
            "נכסים דיגיטליים: ארנק קריפטו (Ethereum / WETH) ומיזם World Liberty Financial",
            "השקעות שוק והון נזיל: קרנות מדד S&P 500 ואג\"ח ממשלת ארה\"ב"
        ],
        "description": "התיק מבוסס על דוחות הגילוי הפיננסי הרשמיים (OGE Form 278e) ומשלב מדיה, נדל\"ן ונכסי קריפטו."
    },
    "pelosi": {
        "name": "ננסי פלוסי (דיווחי קונגרס)",
        "ticker": "NVDA",
        "type": "fund",
        "core_holdings": [
            "NVIDIA (NVDA) - אופציות Call עמוקות (LEAPS)",
            "Broadcom (AVGO)",
            "Apple (AAPL)",
            "Microsoft (MSFT)"
        ],
        "description": "מעקב אחר חוק ה-STOCK Act: התמקדות באופציות Deep In-The-Money לטווח ארוך בענקיות הטכנולוגיה."
    }
}

def get_insider_key(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["אקמן", "ackman", "פרשינג"]):
        return "ackman"
    if any(k in t for k in ["קאת'י", "קאתי", "קטי", "cathie", "wood", "ארק", "arkk"]):
        return "cathie"
    if any(k in t for k in ["ג'נסן", "גנסן", "הואנג", "jensen", "huang"]):
        return "jensen"
    if any(k in t for k in ["דליו", "dalio", "ברידג'ווטר", "ברידגוור"]):
        return "dalio"
    if any(k in t for k in ["טראמפ", "trump", "djt"]):
        return "trump"
    if any(k in t for k in ["פלוסי", "pelosi"]):
        return "pelosi"
    return "cathie"

def fetch_insider_trades(ticker_symbol: str, limit: int = 3) -> list:
    trades = []
    try:
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.insider_transactions
        if df is None or df.empty:
            return []

        for _, row in df.head(limit).iterrows():
            insider = str(row.get("Insider", "בכיר"))
            relation = str(row.get("Position", "בעל עניין"))
            shares = row.get("Shares", 0)
            value = row.get("Value", 0)
            text = str(row.get("Text", ""))
            start_date = str(row.get("Start Date", ""))[:10]

            is_sale = "Sale" in text or (isinstance(shares, (int, float)) and shares < 0)
            tx_type = "🔴 מכירה" if is_sale else "🟢 קנייה"

            val_str = f"{abs(int(value)):,}$" if pd.notna(value) and value != 0 else "לא צוין"
            trades.append({
                "insider": insider,
                "position": relation,
                "date": start_date,
                "type": tx_type,
                "value": val_str
            })
        return trades
    except Exception:
        return []

def format_smart_money_summary(query_text: str = "") -> str:
    key = get_insider_key(query_text)
    profile = INSIDERS_DIRECTORY[key]
    target_ticker = profile["ticker"]
    prof_type = profile.get("type")

    price_str = ""
    try:
        hist = yf.Ticker(target_ticker).history(period="2d")
        if not hist.empty:
            price_str = f" | שער אחרון: {hist['Close'].iloc[-1]:.2f}$"
    except Exception:
        pass

    lines = [
        f"🏛️ **דוח Smart Money מרוכז:**",
        f"👤 **דמות:** {profile['name']}",
        f"🎯 **נכס עיקרי במעקב:** {target_ticker}{price_str}",
        f"ℹ️ {profile['description']}\n"
    ]

    # הצגת אחזקות הליבה
    holdings = profile.get("core_holdings", [])
    if holdings:
        lines.append("📊 **פוזיציות ואחזקות מובילות:**")
        for h in holdings:
            lines.append(f"• {h}")
        lines.append("")

    # אם מדובר בחברה עם עסקאות בכירים (כמו NVDA של ג'נסן)
    if prof_type == "insider":
        trades = fetch_insider_trades(target_ticker, limit=3)
        if trades:
            lines.append("📋 **דיווחים רשמיים אחרונים בחברה:**")
            for t in trades:
                lines.append(f"• {t['insider']} ({t['position']}) | {t['type']} בהיקף {t['value']} ({t['date']})")
            lines.append("")

    lines.append("💡 **דבר המנטור:** אחזקות מוסדיים הן רוח גבית בלבד. אנחנו סוחרי סווינג - לא קונים שום מניה בלי תבנית מחיר נקייה ומעל ממוצע 150!")
    return "\n".join(lines)

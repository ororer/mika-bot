import yfinance as yf
import pandas as pd

INSIDERS_DIRECTORY = {
    "ackman": {
        "name": "ביל אקמן (Pershing Square)",
        "ticker": "PSHZF",
        "type": "fund",
        "core_holdings": "Alphabet (GOOGL), Chipotle (CMG), Hilton (HLT), Howard Hughes (HHH)",
        "description": "קרן Pershing Square מתמקדת בריכוז גבוה של 8-10 חברות ענק איכותיות עם מודל עסקי צפוי וחפיר עמוק."
    },
    "cathie": {
        "name": "קאת'י ווד (ARK Invest)",
        "ticker": "ARKK",
        "type": "etf",
        "description": "קרן החדשנות ARKK משקיעה בחברות צמיחה משבשת, בינה מלאכותית, בלוקצ'יין ורובוטיקה."
    },
    "jensen": {
        "name": "ג'נסן הואנג (NVIDIA)",
        "ticker": "NVDA",
        "type": "insider",
        "description": "מייסד ומנכ\"ל NVIDIA - מעקב אחר דיווחי Form 4 ומימושי מניות תקופתיים (10b5-1)."
    },
    "dalio": {
        "name": "ריי דליו (Bridgewater)",
        "ticker": "SPY",
        "type": "macro",
        "core_holdings": "S&P 500 (SPY), שווקים מתעוררים (IEMG), זהב (GLD), אג\"ח ממשלתיות",
        "description": "אסטרטגיית All-Weather מאקרו: פיזור גלובלי והגנה מתנודתיות מחזורי חוב."
    },
    "trump": {
        "name": "דונלד טראמפ (Trump Media)",
        "ticker": "DJT",
        "type": "insider",
        "description": "מניית סנטימנט ומומנטום פוליטי מובהק ברשת Truth Social."
    },
    "pelosi": {
        "name": "ננסי פלוסי (דיווחי קונגרס)",
        "ticker": "NVDA",
        "type": "congress",
        "core_holdings": "NVIDIA (NVDA), Broadcom (AVGO), Apple (AAPL), Microsoft (MSFT)",
        "description": "התמקדות באופציות Deep In-The-Money Call לטווח ארוך (LEAPS) בענקיות השבבים."
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

def get_etf_holdings(ticker_symbol: str) -> str:
    """שולף את האחזקות המובילות מ-yfinance אם זמין"""
    try:
        t = yf.Ticker(ticker_symbol)
        # ניסיון שליפת טבלת אחזקות מובנית
        holdings = getattr(t, "funds_data", None)
        if holdings and hasattr(holdings, "top_holdings"):
            df = holdings.top_holdings
            if df is not None and not df.empty:
                lines = []
                for _, row in df.head(5).iterrows():
                    sym = row.get("Holding", row.get("Symbol", ""))
                    pct = row.get("Holding Percent", "")
                    lines.append(f"• {sym} ({pct})")
                return "\n".join(lines)
    except Exception:
        pass
    
    # אחזקות ליבה מובילות ומעודכנות עבור ARKK כגיבוי מדויק
    if ticker_symbol == "ARKK":
        return "• Tesla (TSLA)\n• Roku (ROKU)\n• Coinbase (COIN)\n• Block (SQ)\n• Roblox (RBLX)"
    return ""

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

    # אם מדובר בקרן / ETF (כמו קאת'י ווד או אקמן) מציגים את האחזקות
    if prof_type in ["etf", "fund", "macro", "congress"]:
        lines.append("📊 **פוזיציות ואחזקות מובילות בתיק:**")
        etf_data = get_etf_holdings(target_ticker)
        if etf_data:
            lines.append(etf_data)
        elif "core_holdings" in profile:
            lines.append(f"• {profile['core_holdings']}")
        lines.append("")

    # משיכת פעולות אחרונות של בכירים אם מדובר במניה ספציפית
    if prof_type in ["insider", "congress"]:
        trades = fetch_insider_trades(target_ticker, limit=3)
        if trades:
            lines.append("📋 **דיווחים רשמיים אחרונים בחברה:**")
            for t in trades:
                lines.append(f"• {t['insider']} ({t['position']}) | {t['type']} בהיקף {t['value']} ({t['date']})")
            lines.append("")

    lines.append("💡 **דבר המנטור:** אחזקות מוסדיים הן רוח גבית בלבד. אנחנו סוחרי סווינג - לא קונים שום מניה בלי תבנית מחיר נקייה ומעל ממוצע 150!")
    return "\n".join(lines)

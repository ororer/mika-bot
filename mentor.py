import os
from datetime import datetime
import pytz
import google.generativeai as genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# המודלים הנתמכים והמומלצים רשמית על ידי ה-API של גוגל בחשבונך
CANDIDATE_MODELS = [
    "models/gemini-3.5-flash-lite",
    "models/gemini-3.5-flash",
    "models/gemini-3.8-flash"
]

SYSTEM_INSTRUCTION = """
אתה צ'יפ, מנטור סווינג טכני ושנון המלווה קהילת סוחרים.
העקרונות שלך:
1. שפה עברית טבעית, זורמת ומקצועית (סלנג סוחרים איכותי).
2. שמור על המשמעות המקצועית, חדה ומדויקת.
3. שמירה על משמעת, סבלנות וישיבה על הגדר כשאין מהלך מובהק לפי הפלייבוק.
4. אם שואלים למה אין מסחר, נמק במדויק.
5. תשובות תמציתיות, חדות ולעניין (פסקה עד שתיים מקסימום).
"""

def get_current_market_context() -> str:
    tz_ny = pytz.timezone("America/New_York")
    now_ny = datetime.now(tz_ny)
    day_name = now_ny.strftime("%A")
    date_str = now_ny.strftime("%Y-%m-%d")
    time_str = now_ny.strftime("%H:%M")
    return f"תאריך היום (שעון ניו יורק): {date_str} ({day_name}), שעה: {time_str}"

def call_gemini(prompt: str) -> str:
    if not GEMINI_API_KEY:
        return "מפתח ה-API של Gemini אינו מוגדר בסביבה."

    last_error = ""
    for model_name in CANDIDATE_MODELS:
        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=SYSTEM_INSTRUCTION
            )
            response = model.generate_content(prompt, request_options={"timeout": 15})
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            last_error = str(e)
            continue

    return f"צ'יפ כאן: תקלת תקשורת מול ה-AI ({last_error})."

def get_mentor_analysis(ticker: str, result: dict, last_price: float, rsi: float, sma150: float) -> str:
    context = get_current_market_context()
    prompt = f"""
{context}
נתח את מניית {ticker} לפי הנתונים הבאים:
- מחיר אחרון: {last_price:.2f}$
- ממוצע נע 150: {sma150:.2f}$
- מדד RSI (14): {rsi:.1f}
- החלטת מנוע הפלייבוק: {result.get('status')}
- פרטי סטאפ: {result.get('details', 'אין פירוט נוסף')}

תן סיכום מנטור קצר, חד ושנון בסגנון צ'יפ: האם יש כאן מהלך, לשבת על הגדר, או לשמור על משמעת.
"""
    return call_gemini(prompt)

def get_mentor_chat_reply(user_message: str) -> str:
    context = get_current_market_context()
    prompt = f"""
{context}
הודעת המשתמש: "{user_message}"

ענה כצ'יפ המנטור בשפה חופשית, תמציתית, מקצועית ומלאת ביטחון. שמור על תשובה קצרה (1-2 פסקאות).
"""
    return call_gemini(prompt)

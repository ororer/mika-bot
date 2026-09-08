import os
from datetime import datetime
import pytz
import google.generativeai as genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY, transport="rest")

MODEL_NAME = "models/gemini-3.5-flash-lite"

SYSTEM_INSTRUCTION = """
אתה צ'יפ, מנטור סווינג טכני ישראלי חד, מקצועי, שקול ושנון המלווה קהילת סוחרים.

כללי שפה וניסוח קשיחים:
1. עברית בלבד: כתוב בעברית ישראלית טבעית, שוטפת, רהוטה וללא שגיאות.
2. איסור תעתיק עילג: אל תנסה לכתוב מילים מאנגלית באותיות עבריות בצורה משובשת (אסור לכתוב "קאש", "קפיטל", "סטאפים"). השתמש בעברית טבעית: "מזומן", "הון", "תבנית / תוכנית עבודה".
3. מונחים מקצועיים באנגלית: אם משתמשים במונח טכני, כתוב אותו באנגלית תקינה (למשל: Breakout, Setup, Stop Loss, Cash).
4. גישת מסחר: דגש על משמעת ברזל, סבלנות, שמירה על ההון וישיבה ממושמעת על הגדר כשאין תבנית ברורה לפלייבוק.
5. תמציתיות: תשובות ממוקדות וקצרות (1-2 פסקאות בלבד).
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

    try:
        model = genai.GenerativeModel(
            model_name=MODEL_NAME,
            system_instruction=SYSTEM_INSTRUCTION
        )
        response = model.generate_content(prompt)
        if response and response.text:
            return response.text.strip()
        return "לא התקבלה תשובה מהמודל."
    except Exception as e:
        return f"צ'יפ כאן: תקלת תקשורת מול ה-AI ({e})."

def get_mentor_analysis(ticker: str, result: dict, last_price: float, rsi: float, sma150: float) -> str:
    context = get_current_market_context()
    prompt = f"""
{context}
נתח את מניית {ticker} לפי הנתונים הטכניים הבאים:
- מחיר אחרון: {last_price:.2f}$
- ממוצע נע 150: {sma150:.2f}$
- מדד RSI (14): {rsi:.1f}
- החלטת מנוע הפלייבוק: {result.get('status')}
- פרטי סטאפ: {result.get('details', 'אין פירוט נוסף')}

תן סיכום מנטור קצר, חד, בעברית רהוטה ונקייה: מה המצב הטכני, האם יש תבנית כניסה לפי הפלייבוק, או שיושבים על הגדר ושומרים על המזומן.
"""
    return call_gemini(prompt)

def get_mentor_chat_reply(user_message: str) -> str:
    context = get_current_market_context()
    prompt = f"""
{context}
הודעת הסוחר: "{user_message}"

ענה כצ'יפ המנטור בעברית טבעית, חדה, מקצועית וישראלית. שמור על תשובה קצרה (1-2 פסקאות בלבד).
"""
    return call_gemini(prompt)

import os
from datetime import datetime
import pytz
import google.generativeai as genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    # transport='rest' מונע שגיאות gRPC 504 Deadline Exceeded בסביבות ענן כמו Render
    genai.configure(api_key=GEMINI_API_KEY, transport="rest")

MODEL_NAME = "models/gemini-3.5-flash-lite"

SYSTEM_INSTRUCTION = """
אתה צ'יפ, מנטור סווינג טכני מקצועי, חד ושנון שמלווה קהילת סוחרים ישראלית.
עקרונות חובה לתשובות שלך:
1. שפה ועברית: הקפד על עברית ישראלית טבעית ותקנית, נטולת שגיאות כתיב או תרגומים עילגים. כתוב בצורה שוטפת ובגובה העיניים (סלנג סוחרים איכותי ומקצועי).
2. טיקרים ומונחים: השתמש בטיקר המדויק באנגלית כפי שהמשתמש ציין (למשל NBIS עבור נביוס). אל תמציא טיקרים אחרים.
3. פילוסופיית מסחר: שמירה אדוקה על ניהול סיכונים, משמעת ברזל, סטופ לוס מוגדר מראש וסבלנות לשבת על הגדר כשאין סטאפ מובהק לפי הפלייבוק.
4. סגנון: תשובות קצרות, תמציתיות, חדות ולעניין (פסקה עד שתיים מקסימום). ללא מריחות.
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

תן סיכום מנטור קצר, חד, בעברית רהוטה וטבעית: מה התובנה על הנייר, האם יש סטאפ לפלייבוק, או שיושבים על הגדר ושומרים על הכסף.
"""
    return call_gemini(prompt)

def get_mentor_chat_reply(user_message: str) -> str:
    context = get_current_market_context()
    prompt = f"""
{context}
הודעת הסוחר: "{user_message}"

ענה כצ'יפ המנטור בעברית תקנית, טבעית, חדה ומקצועית. שמור על תשובה קצרה וממוקדת (1-2 פסקאות בלבד).
"""
    return call_gemini(prompt)

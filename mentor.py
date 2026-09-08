import os
from datetime import datetime
import pytz
import google.generativeai as genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# רשימת מודלים רשמיים, מהירים ונתמכים בלבד
CANDIDATE_MODELS = [
    "gemini-1.5-flash",
    "gemini-1.5-flash-latest",
    "gemini-1.5-pro"
]

SYSTEM_INSTRUCTION = """
אתה 'צ'יפ' (Chip) – מנטור וסיידקיק מקצועי, חד, כריזמטי ושנון למסחר סווינג טכני, המלווה קהילת סוחרים.
העקרונות שלך:
1. שפה: עברית טבעית, זורמת ומקצועית (סלנג סוחרים איכותי).
2. מונחים טכניים: מותר ורצוי להשתמש במונחים מקצועיים באנגלית או עברית (כגון RSI, SMA 150, Stop Loss, Breakout, Pullback, Ticker). לעולם אל תעיר על השפה שבה המונח כתוב, ואל תתווכח על כללי תרגום.
3. פילוסופיית מסחר: הגנה על הכסף קודמת לרווח, קטיעת הפסדים מהירה, כניסה רק לפי תבניות איכותיות, סבלנות וישיבה על הגדר כשאין מהלך מובהק.
4. ידע כללי ולוח מסחר: אתה מודע לתאריך הנוכחי, לשעות המסחר בארה"ב (שעון ניו יורק) ולחגים שבהם הבורסה סגורה (כגון Labor Day, Memorial Day, 4th of July, Thanksgiving וכו'). אם שואלים למה אין מסחר, נמק במדויק.
5. אורך התשובה: תמציתי, חד ולעניין (פסקה עד שתיים מקסימום).
"""

def get_current_market_context() -> str:
    tz_ny = pytz.timezone("America/New_York")
    now_ny = datetime.now(tz_ny)
    day_name = now_ny.strftime("%A")
    date_str = now_ny.strftime("%Y-%m-%d")
    time_str = now_ny.strftime("%H:%M")
    return f"תאריך היום (שעון ניו יורק): {date_str}, יום: {day_name}, שעה: {time_str}."

def call_gemini(prompt: str) -> str:
    if not GEMINI_API_KEY:
        return "מפתח ה-API של Gemini אינו מוגדר."

    last_error = None
    for model_name in CANDIDATE_MODELS:
        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=SYSTEM_INSTRUCTION
            )
            response = model.generate_content(prompt)
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            last_error = e
            continue

    raise RuntimeError(f"כל המודלים נכשלו. שגיאה אחרונה: {last_error}")

def get_mentor_analysis(ticker: str, engine_result: dict, price: float, rsi: float, sma150: float) -> str:
    if not GEMINI_API_KEY:
        status = engine_result.get("status", "WAIT")
        return f"מצב מנוע: {status}. מחיר: {price:.2f}$, ממוצע 150: {sma150:.2f}$, RSI: {rsi:.1f}."

    context = get_current_market_context()
    prompt = f"""
הקשר זמן: {context}

נתח בקצרה את מניית {ticker} על בסיס הנתונים הטכניים הבאים:
- החלטת מנוע הפלייבוק: {engine_result.get('status')}
- מחיר אחרון: {price:.2f}$
- ממוצע נע 150 יום: {sma150:.2f}$
- מדד RSI: {rsi:.1f}
- פרטים נוספים: {engine_result.get('reason', 'ללא הערות מיוחדות')}

תן סקירת מנטור קצרה, שנונה ומדויקת בסגנון צ'יפ: האם יש כאן הזדמנות לפי הפלייבוק, למה לשים לב, והיכן הסיכון. שמור על תשובה ממוקדת בעברית.
"""
    try:
        return call_gemini(prompt)
    except Exception as e:
        return f"צ'יפ כאן: המנוע מראה {engine_result.get('status')}. מחיר סביב {price:.2f}$, ממוצע 150 ב-{sma150:.2f}$, RSI ב-{rsi:.1f}. ({e})"

def get_mentor_chat_reply(user_message: str) -> str:
    if not GEMINI_API_KEY:
        return "אהלן! אני כאן, שאל אותי על כל טיקר או מושג טכני."

    context = get_current_market_context()
    prompt = f"""
הקשר זמן נוכחי: {context}

הודעה מחבר קהילה:
"{user_message}"

השב לו בקצרה, בביטחון, בהומור קל ובמקצועיות בתור צ'יפ המנטור. אם הוא שואל לגבי מסחר היום או זמנים, התבסס על התאריך והשעה בניו יורק כדי לענות במדויק.
"""
    try:
        return call_gemini(prompt)
    except Exception as e:
        return f"שומע אותך! יש כרגע עומס קל בחיבור: {e}"

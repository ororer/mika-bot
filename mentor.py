import os
import google.generativeai as genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

MODEL_NAME = "gemini-2.5-flash"

SYSTEM_INSTRUCTION = """
אתה 'צ'יפ' (Chip) – מנטור וסיידקיק מקצועי, חד, כריזמטי ושנון למסחר סווינג טכני, המלווה קהילת סוחרים.
העקרונות שלך:
1. שפה: עברית טבעית, זורמת ומקצועית (סלנג סוחרים איכותי). 
2. מונחים טכניים: מותר ורצוי להשתמש במונחים מקצועיים באנגלית או עברית (כגון RSI, SMA 150, Stop Loss, Breakout, Pullback, Ticker). לעולם אל תעיר על השפה שבה המונח כתוב, ואל תתווכח על כללי תרגום.
3. פילוסופיית מסחר: הגנה על הכסף קודמת לרווח, קטיעת הפסדים מהירה, כניסה רק לפי תבניות איכותיות, סבלנות וישיבה על הגדר כשאין מהלך מובהק.
4. אורך התשובה: תמציתי, חד ולעניין (פסקה עד שתיים מקסימום).
"""

def get_mentor_analysis(ticker: str, engine_result: dict, price: float, rsi: float, sma150: float) -> str:
    if not GEMINI_API_KEY:
        status = engine_result.get("status", "WAIT")
        return f"מצב מנוע: {status}. מחיר: {price:.2f}$, ממוצע 150: {sma150:.2f}$, RSI: {rsi:.1f}."

    prompt = f"""
נתח בקצרה את מניית {ticker} על בסיס הנתונים הטכניים הבאים:
- החלטת מנוע הפלייבוק: {engine_result.get('status')}
- מחיר אחרון: {price:.2f}$
- ממוצע נע 150 יום: {sma150:.2f}$
- מדד RSI: {rsi:.1f}
- פרטים נוספים: {engine_result.get('reason', 'ללא הערות מיוחדות')}

תן סקירת מנטור קצרה, שנונה ומדויקת בסגנון צ'יפ: האם יש כאן הזדמנות לפי הפלייבוק, למה צריך לשים לב (למשל תמיכה, ממוצע 150, פריצה או הגעה לקיצון), והיכן הסיכון. שמור על תשובה ממוקדת בעברית.
"""
    try:
        model = genai.GenerativeModel(model_name=MODEL_NAME, system_instruction=SYSTEM_INSTRUCTION)
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"צ'יפ כאן: המנוע מראה {engine_result.get('status')}. שים לב להתנהגות המחיר סביב ממוצע 150 ({sma150:.2f}$) וה-RSI ({rsi:.1f}). (הערת מערכת: {e})"

def get_mentor_chat_reply(user_message: str) -> str:
    if not GEMINI_API_KEY:
        return "אהלן! אני כאן, שאל אותי על כל טיקר או מושג טכני."

    prompt = f"""
הודעה מחבר קהילה:
"{user_message}"

השב לו בקצרה, בביטחון, בהומור קל ובמקצועיות בתור צ'יפ המנטור.
"""
    try:
        model = genai.GenerativeModel(model_name=MODEL_NAME, system_instruction=SYSTEM_INSTRUCTION)
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"שומע אותך! יש כרגע עומס קל בחיבור: {e}"

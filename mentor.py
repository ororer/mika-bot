import os
from google import genai

def get_mentor_analysis(ticker: str, engine_result: dict, last_price: float, rsi: float, sma150: float) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "שגיאה: מפתח GEMINI_API_KEY אינו מוגדר."

    client = genai.Client(api_key=api_key)

    system_instruction = (
        "אתה משמש כמנטור המסחר מיכה סטוקס ומנתח מניות אך ורק לפי הפלייבוק הטכני של 16 השיעורים שלך.\n"
        "טון הדיבור שלך: חד, מקצועי, ללא פילטרים, שומר על ניהול סיכונים קפדני ולא מתפתה לרדוף אחרי מניות.\n\n"
        "עקרונות הברזל שלך:\n"
        "1. שום דבר טוב לא קורה מתחת לממוצעים הגדולים (SMA 150/200) – לא נוגעים בסכין נופלת ולא מנחשים תחתיות.\n"
        "2. לא קונים מניה במתיחת יתר (RSI מעל 70) – לא משלמים פרמיה מוגזמת.\n"
        "3. פטיש (Hammer) מחייב יום אישור המשכיות (Follow-Through) ירוק – לא קונים פטיש בודד ללא אישור.\n"
        "4. אין כניסה ללא שפל מוגדר (Tradeable Bottom) וסטופ-לוס ברור.\n\n"
        "תפקידך להסביר למשתמש את המצב של המניה בעברית בהירה, ישירה ובגובה העיניים, "
        "תוך התייחסות למספרים ולסטטוס שחולצו מהגרף."
    )

    user_prompt = f"""
ניתוח מניה: {ticker}
- מחיר אחרון: {last_price:.2f}$
- ממוצע נע 150: {sma150:.2f}$
- RSI (14): {rsi:.2f}
- החלטת המנוע הטכני: {engine_result.get('status')}
- הודעת מנוע: {engine_result.get('message')}
- תבנית שזוהתה: {engine_result.get('setup', 'אין')}
- סטופ-לוס מחושב: {engine_result.get('stop_loss', 'לא רלוונטי')}

תן את חוות הדעת שלך על הגרף ב-2 עד 3 פסקאות קצרות וממוקדות.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_prompt,
        config={"system_instruction": system_instruction}
    )

    return response.text

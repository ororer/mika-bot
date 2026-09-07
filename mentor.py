import os
from google import genai
from google.genai import types

CHIP_SYSTEM_INSTRUCTION = (
    "אתה צ'יפ (Chip) – מנטור מסחר סווינג אישי, קליל, חד וחכם.\n"
    "אתה מנתח שוק ומניות אך ורק לפי מתודולוגיית הפלייבוק הטכני (16 שיעורי הפלייבוק).\n"
    "האופי שלך: שותף קליל, חברי, בגובה העיניים, אבל כשזה מגיע לגרפים ולסיכון – אתה חד כמו תער, "
    "משמעתי מאוד, לא מתפתה לרדוף אחרי מניות, וללא פילטרים כשמישהו מנסה לעשות שטויות בתיק.\n\n"
    "עקרונות הברזל שלך:\n"
    "1. שום דבר טוב לא קורה מתחת לממוצע 150/200 – לעולם לא נוגעים בסכין נופלת ולא מנחשים תחתיות.\n"
    "2. לא קונים מניה מתוחה (RSI מעל 70) – לא משלמים פרמיה מוגזמת, יושבים על קש.\n"
    "3. נר פטיש (Hammer) מחייב יום אישור המשכיות (Follow-Through) ירוק – לא קונים פטיש בודד.\n"
    "4. חובת סטופ-לוס מוגדר ושפל ברור (Tradeable Bottom). ניהול סיכונים קפדני (1%-2% סיכון מהתיק).\n"
    "5. המטרה הראשונה: להגן על הכסף. המטרה השנייה: לתפוס מהלכים איכותיים.\n\n"
    "אם שואלים אותך מי אתה או איך קוראים לך, תציג את עצמך בתור צ'יפ (Chip) בשמחה ובקצרה.\n"
    "ענה תמיד בעברית שוטפת, קולחת וטבעית."
)

def _call_gemini(prompt_text: str) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "שגיאה: חסר GEMINI_API_KEY."

    client = genai.Client(api_key=api_key)
    
    # פנייה ישירה למודל יציב ומהיר בלי עיכובים
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_text,
            config=types.GenerateContentConfig(
                system_instruction=CHIP_SYSTEM_INSTRUCTION,
                temperature=0.7
            )
        )
        if response and response.text:
            return response.text
    except Exception as e:
        print(f"[שגיאה ב-Gemini]: {e}")

    return "סורי, היה עומס קל ברשת. נסה לשאול אותי שוב עוד רגע!"

def get_mentor_analysis(ticker: str, engine_result: dict, last_price: float, rsi: float, sma150: float) -> str:
    prompt = f"""
ניתוח מניה: {ticker}
- מחיר נוכחי: {last_price:.2f}$
- ממוצע נע 150: {sma150:.2f}$
- RSI (14): {rsi:.2f}
- החלטת המנוע הטכני: {engine_result.get('status')}
- הסבר טכני: {engine_result.get('message')}
- תבנית שזוהתה: {engine_result.get('setup', 'אין')}
- סטופ-לוס מחושב: {engine_result.get('stop_loss', 'לא רלוונטי')}

תן את חוות הדעת שלך בתור צ'יפ ב-2 פסקאות קצרות, חדות וממוקדות.
"""
    return _call_gemini(prompt)

def get_mentor_chat_reply(user_question: str) -> str:
    prompt = f"משתמש שואל אותך: {user_question}\nענה לו ישירות כצ'יפ."
    return _call_gemini(prompt)

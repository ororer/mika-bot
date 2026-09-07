import os
from google import genai

CHIP_SYSTEM_INSTRUCTION = (
    "אתה צ'יפ (Chip) – מנטור מסחר סווינג טכני אישי, קליל, חד וחכם.\n"
    "אתה מנתח שוק ומניות אך ורק לפי מתודולוגיית הפלייבוק הטכני (16 שיעורי הפלייבוק).\n"
    "האופי שלך: שותף קליל, ידידותי, בגובה העיניים, אבל כשזה מגיע לגרפים ולסיכון – אתה חד כמו תער, "
    "משמעתי מאוד, לא מתפתה לרדוף אחרי מניות, וללא פילטרים כשמישהו מנסה לעשות שטויות בתיק.\n\n"
    "עקרונות הברזל שמובילים אותך:\n"
    "1. שום דבר טוב לא קורה מתחת לממוצע 150/200 – לעולם לא נוגעים בסכין נופלת ולא מנחשים תחתיות.\n"
    "2. לא קונים מניה מתוחה (RSI מעל 70) – לא משלמים פרמיה מוגזמת, יושבים על קש.\n"
    "3. נר פטיש (Hammer) מחייב יום אישור המשכיות (Follow-Through) ירוק – לא קונים פטיש בודד.\n"
    "4. חובת סטופ-לוס מוגדר ושפל ברור (Tradeable Bottom). ניהול סיכונים קפדני (1%-2% סיכון מהתיק).\n"
    "5. המטרה הראשונה: להגן על הכסף. המטרה השנייה: לתפוס מהלכים איכותיים.\n\n"
    "ענה בעברית שוטפת, קולחת וטבעית, כמו חבר שמבין עניין בגרפים."
)

candidate_models = [
    "gemini-3.6-flash",
    "gemini-flash-latest",
    "gemini-2.5-flash",
    "gemini-3.7-flash"
]

def _generate_with_fallback(client, contents: str) -> str:
    for model_name in candidate_models:
        try:
            res = client.models.generate_content(
                model=model_name,
                contents=contents,
                config={"system_instruction": CHIP_SYSTEM_INSTRUCTION}
            )
            if res and res.text:
                return res.text
        except Exception as e:
            print(f"[דיבוג] ניסיון עבור {model_name} נכשל: {e}")
            continue
    return "משהו קצת התבלבל לי בחיבור לשרת, זרוק לי את השאלה שוב עוד רגע."

def get_mentor_analysis(ticker: str, engine_result: dict, last_price: float, rsi: float, sma150: float) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "שגיאה: GEMINI_API_KEY חסר."

    client = genai.Client(api_key=api_key)
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
    return _generate_with_fallback(client, prompt)

def get_mentor_chat_reply(user_question: str) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "שגיאה: GEMINI_API_KEY חסר."

    client = genai.Client(api_key=api_key)
    prompt = f"המשתמש שואל אותך: \"{user_question}\"\nענה לו בתור צ'יפ, בקלילות ובמקצועיות לפי עקרונות הפלייבוק וניהול הסיכונים שלך."
    return _generate_with_fallback(client, prompt)

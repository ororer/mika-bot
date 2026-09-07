import os
from google import genai

MICHA_SYSTEM_INSTRUCTION = (
    "אתה מנטור המסחר מיכה סטוקס. אתה עונה ומנתח אך ורק לפי הפלייבוק הטכני של 16 השיעורים שלך.\n"
    "טון הדיבור שלך: חד, מקצועי, דיבורי, ישיר, ללא פילטרים, שומר על ניהול סיכונים קפדני.\n\n"
    "עקרונות הברזל שלך:\n"
    "1. שום דבר טוב לא קורה מתחת לממוצע 150/200 – לעולם לא נוגעים בסכין נופלת ולא מנחשים תחתיות.\n"
    "2. לא קונים מניה מתוחה (RSI מעל 70) – לא משלמים פרמיה מוגזמת, יושבים על קש.\n"
    "3. נר פטיש (Hammer) מחייב יום אישור המשכיות (Follow-Through) ירוק – לא קונים פטיש בודד.\n"
    "4. חובת סטופ-לוס מוגדר ושפל ברור (Tradeable Bottom). סיכון קבוע של 1%-2% מהתיק.\n"
    "5. מטרתך להגן על ההון של הסוחר לפני רווחים.\n\n"
    "ענה בעברית שוטפת, טבעית ובגובה העיניים, כמו שאתה מדבר בסרטונים ובקהילה."
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
                config={"system_instruction": MICHA_SYSTEM_INSTRUCTION}
            )
            if res and res.text:
                return res.text
        except Exception as e:
            print(f"[דיבוג] ניסיון עבור {model_name} נכשל: {e}")
            continue
    return "משהו השתבש בחיבור לשרת, נסה לשאול שוב עוד רגע."

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

תן את חוות הדעת שלך ב-2 פסקאות ממוקדות בסגנון של מיכה.
"""
    return _generate_with_fallback(client, prompt)

def get_mentor_chat_reply(user_question: str) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "שגיאה: GEMINI_API_KEY חסר."

    client = genai.Client(api_key=api_key)
    prompt = f"המשתמש שואל אותך: \"{user_question}\"\nענה לו בתור מיכה לפי עקרונות המסחר שלך."
    return _generate_with_fallback(client, prompt)

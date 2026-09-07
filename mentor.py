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
    "ענה תמיד בעברית שוטפת, קולחת וטבעית. תהיה תכליתי, קצר וחד."
)

_api_key = os.environ.get("GEMINI_API_KEY")
_client = genai.Client(api_key=_api_key) if _api_key else None

CANDIDATE_MODELS = [
    "gemini-flash-latest",
    "gemini-pro-latest",
    "gemini-3.6-flash"
]

def _call_gemini(prompt_text: str) -> str:
    if not _client:
        print("[שגיאה]: חסר GEMINI_API_KEY", flush=True)
        return "שגיאה: חסר GEMINI_API_KEY."

    config = types.GenerateContentConfig(
        system_instruction=CHIP_SYSTEM_INSTRUCTION,
        temperature=0.6,
        max_output_tokens=350
    )

    for model_name in CANDIDATE_MODELS:
        try:
            print(f"[Chip] מנסה מודל: {model_name}...", flush=True)
            response = _client.models.generate_content(
                model=model_name,
                contents=prompt_text,
                config=config
            )
            if response and response.text:
                print(f"[Chip] הצלחה במודל: {model_name}", flush=True)
                return response.text.strip()
        except Exception as e:
            print(f"[Chip] שגיאה במודל {model_name}: {e}", flush=True)
            continue

    return "כרגע יש עומס שרתים זמני ב-API. המתן דקה ונסה שוב."

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

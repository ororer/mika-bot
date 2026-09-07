import os
import time
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
    "ענה תמיד אך ורק בעברית קולחת, טבעית ומלאה. היה תמציתי ומדויק – ללא שימוש באנגלית כלל."
)

_api_key = os.environ.get("GEMINI_API_KEY")
_client = genai.Client(api_key=_api_key) if _api_key else None
_active_model = None

def _get_best_model():
    """מאתר דינמית את מודל ה-Flash התקף ביותר מחשבון הגוגל שלך"""
    global _active_model
    if _active_model:
        return _active_model

    if not _client:
        return "gemini-2.5-flash"

    try:
        models = list(_client.models.list())
        flash_models = [m.name for m in models if "flash" in m.name.lower()]
        if flash_models:
            # בוחר את מודל ה-flash הראשון שקיים בחשבון
            _active_model = flash_models[0]
            print(f"[Chip AI] נבחר מודל מאומת: {_active_model}", flush=True)
            return _active_model
    except Exception as e:
        print(f"[Chip AI] שגיאה באיתור מודלים: {e}", flush=True)

    _active_model = "gemini-2.5-flash"
    return _active_model

def _call_gemini(prompt_text: str) -> str:
    if not _client:
        print("[שגיאה]: חסר GEMINI_API_KEY", flush=True)
        return "שגיאה: חסר GEMINI_API_KEY במערכת."

    model_to_use = _get_best_model()

    config = types.GenerateContentConfig(
        system_instruction=CHIP_SYSTEM_INSTRUCTION,
        temperature=0.6,
        max_output_tokens=800
    )

    # עד 3 ניסיונות במקרה של שיהוק 503 ברשת
    for attempt in range(3):
        try:
            response = _client.models.generate_content(
                model=model_to_use,
                contents=prompt_text,
                config=config
            )
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            print(f"[Chip Gemini] ניסיון {attempt + 1} במודל {model_to_use} נכשל: {e}", flush=True)
            time.sleep(1.5)

    return "סורי, יש כרגע עומס קל בשרתי הניתוח של גוגל. תן לי חצי דקה ונסה שוב."

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

תן את חוות הדעת שלך בתור צ'יפ ב-2 פסקאות קצרות, חדות וממוקדות בעברית בלבד.
"""
    return _call_gemini(prompt)

def get_mentor_chat_reply(user_question: str) -> str:
    prompt = f"משתמש שואל אותך: {user_question}\nענה לו ישירות כצ'יפ בעברית מלאה בלבד."
    return _call_gemini(prompt)

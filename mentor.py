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
    "ענה תמיד אך ורק בעברית מלאה, שוטפת, קולחת וטבעית. אל תשתמש באנגלית כלל.\n"
    "היה תמציתי ומדויק – 2 פסקאות קצרות ולעניין."
)

_api_key = os.environ.get("GEMINI_API_KEY")
_client = genai.Client(api_key=_api_key) if _api_key else None

def _get_supported_models():
    """מציג ומחזיר את המודלים הנתמכים בחשבון"""
    if not _client:
        return ["gemini-3.6-flash"]
    try:
        all_models = list(_client.models.list())
        # סינון רק למודלים שתומכים ב-generateContent
        valid = [
            m.name.replace("models/", "")
            for m in all_models
            if hasattr(m, "supported_generation_methods") and "generateContent" in (m.supported_generation_methods or [])
        ]
        if not valid:
            valid = [m.name.replace("models/", "") for m in all_models]
        print(f"[Chip Diagnostics] מודלים זמינים במפתח שלך: {valid}", flush=True)
        return valid
    except Exception as e:
        print(f"[Chip Diagnostics] לא ניתן לשלוף רשימת מודלים: {e}", flush=True)
        return ["gemini-3.6-flash"]

# טעינת רשימת המודלים התקפה לחשבון
AVAILABLE_MODELS = _get_supported_models()

def _call_gemini(prompt_text: str) -> str:
    if not _client:
        print("[שגיאה]: חסר GEMINI_API_KEY", flush=True)
        return "שגיאה: חסר GEMINI_API_KEY בהגדרות Render."

    config = types.GenerateContentConfig(
        system_instruction=CHIP_SYSTEM_INSTRUCTION,
        temperature=0.6,
        max_output_tokens=800
    )

    # נסדר עדיפות: קודם 3.6-flash, ואחר כך שאר המודלים שנמצאו בחשבון
    models_to_try = []
    if "gemini-3.6-flash" in AVAILABLE_MODELS:
        models_to_try.append("gemini-3.6-flash")
    for m in AVAILABLE_MODELS:
        if m not in models_to_try and "flash" in m.lower():
            models_to_try.append(m)

    if not models_to_try:
        models_to_try = ["gemini-3.6-flash"]

    last_error = ""
    for model_name in models_to_try:
        for attempt in range(2):
            try:
                print(f"[Chip API] שולח בקשה למודל: {model_name} (ניסיון {attempt + 1})...", flush=True)
                response = _client.models.generate_content(
                    model=model_name,
                    contents=prompt_text,
                    config=config
                )
                if response and response.text:
                    print(f"[Chip API] הצלחה עם מודל: {model_name}!", flush=True)
                    return response.text.strip()
            except Exception as e:
                last_error = str(e)
                print(f"[Chip API] שגיאה במודל {model_name}: {e}", flush=True)
                time.sleep(1)

    return f"שגיאת תקשורת מול גוגל: {last_error}"

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

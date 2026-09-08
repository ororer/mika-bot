import os
import google.generativeai as genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

SYSTEM_PROMPT = """
אתה צ'יפ, מנטור מקצועי ומנוסה למסחר סווינג בבורסה האמריקאית.
הגישה שלך:
1. מקצועית, עניינית ופרקטית. ללא התנשאות, ללא ציניות וללא נזיפות מיותרות. 
2. מטרתך לסייע לסוחר לקבל החלטות מבוססות נתונים ומשמעת ברזל.
3. מתודולוגיית המסחר שלך:
   - מסחר סווינג לפי מומנטום ומבנה שוק.
   - מניות מעל ממוצע 150 ו-200 בלבד (מגמה עולה).
   - זיהוי תבניות התכווצות תנודתיות (VCP) והתייבשות מחזורים לפני פריצה.
   - מחזור יחסי גבוה (RVOL > 1.2) בפריצה כאישור לכניסת כסף מוסדי.
   - ניהול סיכונים קפדני: חיתוך הפסדים קצרים (בדרך כלל 5%-8% מקסימום, או שבירת תמיכה/נר פריצה). יחס סיכוי/סיכון של לפחות 1:2.
4. מתן מענה:
   - כששואלים אותך על סטופ לוס או פוזיציה פתוחה, תן הדרכה טכנית ברורה: היכן ממוקמת רמת המפתח הטכנית, מה המשמעות של היות המניה מתחת לממוצעים, וכיצד למזער נזקים לפי הספר.
   - השפה שלך: עברית רהוטה, מקצועית וטבעית.
"""

_active_model = None

def get_initialized_model():
    """
    מאתר באופן דינמי את המודל הזמין והמתאים ביותר בחשבון ה-API של המשתמש.
    מונע שגיאות 404 כתוצאה משינויי שמות מודלים בגוגל.
    """
    global _active_model
    if _active_model is not None:
        return _active_model

    if not GEMINI_API_KEY:
        print("[Mentor Error] GEMINI_API_KEY חסר בסביבת הריצה", flush=True)
        return None

    genai.configure(api_key=GEMINI_API_KEY)

    preferred_candidates = [
        "models/gemini-1.5-flash",
        "models/gemini-1.5-flash-latest",
        "models/gemini-2.0-flash",
        "models/gemini-1.5-pro",
        "models/gemini-pro"
    ]

    try:
        available_models = [
            m.name for m in genai.list_models()
            if 'generateContent' in m.supported_generation_methods
        ]
        print(f"[Mentor Init] מודלים זמינים בחשבון: {available_models}", flush=True)

        for candidate in preferred_candidates:
            if candidate in available_models:
                _active_model = genai.GenerativeModel(candidate)
                print(f"[Mentor Init] נבחר מודל פעיל: {candidate}", flush=True)
                return _active_model

        if available_models:
            _active_model = genai.GenerativeModel(available_models[0])
            print(f"[Mentor Init] נבחר מודל חלופי: {available_models[0]}", flush=True)
            return _active_model

    except Exception as e:
        print(f"[Mentor Init Warning] שגיאה במשיכת רשימת מודלים ({e}), פונה למודל ברירת מחדל.", flush=True)

    _active_model = genai.GenerativeModel("gemini-1.5-flash")
    return _active_model

def query_gemini(prompt_body: str) -> str:
    model = get_initialized_model()
    if not model:
        return "מפתח GEMINI_API_KEY אינו מוגדר כראוי במערכת."

    full_prompt = f"{SYSTEM_PROMPT}\n\n---\nפניית המשתמש / נתוני המערכת:\n{prompt_body}"

    try:
        response = model.generate_content(full_prompt)
        if response and response.text:
            return response.text.strip()
        return "לא התקבלה תשובה משרתי הניתוח."
    except Exception as e:
        print(f"[Mentor Execution Error] {e}", flush=True)
        # נסיון אחרון עם מודל גיבוי גנרי במקרה של כשל נקודתי
        try:
            fallback = genai.GenerativeModel("gemini-pro")
            response = fallback.generate_content(full_prompt)
            if response and response.text:
                return response.text.strip()
        except Exception:
            pass
        return f"שגיאה בהפעלת שירות הבינה המלאכותית: {e}"

def get_mentor_analysis(ticker: str, result: dict, metrics: dict) -> str:
    setup = result.get('setup', 'ללא סטאפ מוגדר')
    status = result.get('status', 'ניטרלי')
    rsi = metrics.get('rsi', 0)
    rvol = metrics.get('rvol', 0)
    sma150 = metrics.get('sma150', 0)
    close = metrics.get('close', 0)
    atr = metrics.get('atr', 0)

    prompt = f"""
נתח את המניה {ticker} עבור סוחר סווינג על סמך הנתונים הטכניים הבאים:
- מחיר אחרון: {close:.2f}$
- ממוצע נע 150: {sma150:.2f}$
- מדד חוזק יחסי (RSI): {rsi:.1f}
- מחזור יחסי (RVOL): {rvol:.2f}
- תנודתיות ממוצעת (ATR): {atr:.2f}$
- אבחנת מנוע הפלייבוק: {status} ({setup})

הנחיות לתשובה:
1. ספק סיכום טכני של 2-4 משפטים ממוקדים.
2. הסבר בקצרה מה משמעות מיקום המחיר ביחס לממוצע 150 והאם המחזורים (RVOL) מראים עניין מוסדי או יובש.
3. תן שורת תחתונה מעשית: האם להמתין על הגדר, איפה לחפש אישור לתבנית (כגון VCP או פריצה), ובאיזו רמה טכנית שוכנת התמיכה/סטופ לוס.
"""
    return query_gemini(prompt)

def get_mentor_chat_reply(user_text: str) -> str:
    prompt = f"""
המשתמש פנה אליך בהודעה הבאה:
"{user_text}"

הנחיות לתשובה:
1. ענה בצורה מקצועית, מעשית וממוקדת סווינג (ללא עוקצנות או ביטול).
2. אם המשתמש מתייעץ לגבי כניסה שביצע או מיקום סטופ (למשל נכנס במחיר מסוים במניה שהוזכרה קודם), הסבר לו כיצד לנהל את הסיכון: לחשב את אחוז ההפסד הנוכחי, להגדיר קו אדום מתחת לשפל המבני הקרוב או לצאת אם הטרייד שבר את תוכנית המסחר המקורית.
3. אם ההודעה עוסקת במניה ששמה לא ברור, בקש בצורה פשוטה את סמל הטיקר באנגלית.
"""
    return query_gemini(prompt)

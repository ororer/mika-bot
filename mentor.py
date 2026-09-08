import os
import google.generativeai as genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

SYSTEM_PROMPT = """
אתה צ'יפ, מנטור מקצועי ומנוסה למסחר סווינג בבורסה האמריקאית.
הגישה שלך:
1. עניינית, טכנית ופרקטית. ללא התנשאות וללא נזיפות. אל תטיף מוסר גם אם המשתמש טעה.
2. מתודולוגיית המסחר: 
   - מניות מעל ממוצע 150 בלבד.
   - זיהוי תבניות VCP והתייבשות מחזורים לפני פריצה. 
   - מחזור יחסי גבוה (RVOL > 1.2) כאישור בפריצה.
3. מתן מענה:
   - קבע סטופ לוס מתחת לנר הפריצה או לרמת התמיכה האחרונה (שפל קודם).
   - חשב את המרחק באחוזים למען ניהול סיכונים תקני במידה והמשתמש ציין מחיר קנייה.
4. עברית רהוטה וברורה.
"""

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def get_model():
    return genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=SYSTEM_PROMPT
    )

def query_gemini(prompt_text: str) -> str:
    if not GEMINI_API_KEY:
        return "המערכת מנותקת כרגע (חסר מפתח AI). עבוד לפי הנתונים היבשים."
        
    try:
        model = get_model()
        response = model.generate_content(prompt_text)
        if response and response.text:
            return response.text.strip()
        return "לא התקבלה תובנה חכמה מהמודל."
    except Exception as e:
        print(f"[Mentor API Error] {e}", flush=True)
        return "אני קצת עמוס כרגע. תעיף מבט בנתונים הטכניים מעלה ונהל סיכונים לפי הספר."

def get_mentor_analysis(ticker: str, result: dict, metrics: dict, user_prompt: str = "") -> str:
    setup = result.get('setup', 'ללא סטאפ')
    status = result.get('status', 'ניטרלי')
    rsi = metrics.get('rsi', 0)
    rvol = metrics.get('rvol', 0)
    sma150 = metrics.get('sma150', 0)
    close = metrics.get('close', 0)
    
    prompt = f"""
נתח את המניה {ticker} עבור סוחר סווינג.
נתונים טכניים נוכחיים:
- מחיר: {close:.2f}$
- ממוצע 150: {sma150:.2f}$
- RSI: {rsi:.1f}
- RVOL: {rvol:.2f}
- החלטת מנוע: {status} ({setup})

הודעת המשתמש (אם יש שאלת המשך כמו 'קניתי ב-X' או 'איפה סטופ'): 
"{user_prompt}"

בנה תובנה טכנית קצרה (3-4 משפטים). אם המשתמש ציין מחיר קנייה, התייחס לסטופ ביחס לנתונים. אם אין שאלה ספציפית, הסבר בקצרה את תמונת המצב והמגמה.
"""
    return query_gemini(prompt)

def get_mentor_chat_reply(user_text: str) -> str:
    prompt = f"""
המשתמש פנה אליך בהודעה הבאה ללא הקשר לטיקר מסוים:
"{user_text}"

ענה עניינית. אם הוא מבקש ניתוח למניה מסוימת, בקש ממנו להקליד את הטיקר באנגלית.
"""
    return query_gemini(prompt)

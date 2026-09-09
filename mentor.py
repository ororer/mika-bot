import os
import time
from google import genai
from google.genai import types

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

SYSTEM_PROMPT = """
אתה צ'יפ (Chip), עוזר AI חכם ורב-תכליתי.
יש לך שתי מומחיות עיקריות:
1. מנטור מקצועי ומנוסה למסחר סווינג בבורסה האמריקאית (מתודולוגיית מסחר: מניות מעל ממוצע 150, תבניות VCP, מחזורים חריגים, ניהול סיכונים).
2. מודל שפה חכם (AI Assistant) לכל שאלה כללית, טכנולוגית, מדעית, תכנותית או יומיומית.

כללי התנהגות:
- כאשר המשתמש שואל על שוק ההון או מניות, הייה ענייני, טכני ופרקטי. אל תטיף מוסר גם אם המשתמש טעה. קבע סטופ לוס מתחת לנר הפריצה או לרמת התמיכה האחרונה, וחשב מרחק באחוזים למען ניהול סיכונים.
- כאשר המשתמש שואל שאלות כלליות, מורכבות או מבקש קוד/עזרה בנושאים אחרים, ענה לו במלוא הידע המקיף שלך בצורה מפורטת, מקצועית וחברית.
- ענה תמיד בעברית רהוטה וברורה.
"""

# אתחול הלקוח החדש של גוגל
client = None
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)

def query_gemini(prompt_text: str, retries: int = 3) -> str:
    if not client:
        return "המערכת מנותקת כרגע (חסר מפתח AI). עבוד לפי הנתונים היבשים."
        
    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model='gemini-1.5-flash',  # שונה לגרסה היציבה כדי למנוע קריסות ועומסים
                contents=prompt_text,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                )
            )
            if response and response.text:
                return response.text.strip()
            return "לא התקבלה תובנה חכמה מהמודל."
            
        except Exception as e:
            print(f"[Mentor API Error - Attempt {attempt + 1}/{retries}] {e}", flush=True)
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))  # ממתין קצת יותר זמן בין ניסיון לניסיון
            else:
                return "אני קצת עמוס כרגע. תעיף מבט בנתונים הטכניים מעלה ונהל סיכונים לפי הספר."

def get_mentor_analysis(ticker: str, result: dict, metrics: dict, user_prompt: str = "") -> str:
    setup = result.get('setup', 'ללא סטאפ')
    status = result.get('status', 'ניטרלי')
    rsi = metrics.get('rsi', 0)
    rvol = metrics.get('rvol', 0)
    sma20 = metrics.get('sma20', 0)
    sma150 = metrics.get('sma150', 0)
    close = metrics.get('close', 0)
    
    prompt = f"""
נתח את המניה {ticker} עבור סוחר סווינג.
נתונים טכניים נוכחיים:
- מחיר: {close:.2f}$
- ממוצע 20: {sma20:.2f}$
- ממוצע 150: {sma150:.2f}$
- RSI: {rsi:.1f}
- RVOL: {rvol:.2f}
- החלטת מנוע: {status} ({setup})

הודעת המשתמש (אם יש שאלת המשך כמו 'מה עם ממוצע 20' או 'איפה סטופ'): 
"{user_prompt}"

בנה תובנה טכנית קצרה (3-4 משפטים). התייחס לשאלת המשתמש באופן ישיר - אם שאל על נתון מסוים כמו ממוצע 20 או מחיר קנייה, נתח את הנתון הזה. אם אין שאלה ספציפית, הסבר בקצרה את תמונת המצב והמגמה.
"""
    return query_gemini(prompt)

def get_mentor_chat_reply(user_text: str) -> str:
    prompt = f"""
המשתמש פנה אליך בהודעה הבאה:
"{user_text}"

ענה לו כמודל AI חכם. אם זו שאלה מורכבת, בקשה לקוד או ידע כללי, ענה באריכות ובפירוט הנדרש כמו עוזר וירטואלי מעולה. 
רק אם הוא מבקש במפורש ניתוח טכני של מניה ספציפית אבל שכח לציין את שם המניה (טיקר) באנגלית, בקש ממנו להקליד את הטיקר.
"""
    return query_gemini(prompt)

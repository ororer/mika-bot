import os
import time
import yfinance as yf
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

client = None
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)

def query_gemini(prompt_text: str, retries: int = 3) -> str:
    if not client:
        return "המערכת מנותקת כרגע (חסר מפתח AI). עבוד לפי הנתונים היבשים."
        
    backoff_times = [5, 10, 20]
    
    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model='gemini-3.6-flash',
                contents=prompt_text,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.7,
                )
            )
            if response and response.text:
                return response.text.strip()
            return "לא התקבלה תובנה חכמה מהמודל."
            
        except Exception as e:
            error_str = str(e)
            print(f"[Mentor API Error - Attempt {attempt + 1}/{retries}] {error_str}", flush=True)
                
            if attempt < retries - 1:
                wait_time = backoff_times[attempt]
                print(f"[Mentor API] ממתין {wait_time} שניות לפני ניסיון נוסף...", flush=True)
                time.sleep(wait_time)
            else:
                return "השרתים של גוגל עמוסים עד אפס מקום כרגע (שגיאת 503). נסה שוב בעוד כמה דקות."

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

def get_mentor_chat_reply(user_text: str, history: list = None) -> str:
    if history is None:
        history = []
        
    transcript = ""
    if history:
        transcript += "היסטוריית השיחה הקודמת (לצורך הקשר בלבד):\n"
        for msg in history:
            role = "משתמש" if msg["role"] == "user" else "צ'יפ"
            transcript += f"{role}: {msg['text']}\n"
        transcript += "---\n\n"
        
    prompt = f"""{transcript}המשתמש פנה בהודעה הבאה:
"{user_text}"

ענה לו כמודל AI חכם. התחשב בהקשר השיחה הקודמת במידת הצורך כדי לשמור על עקביות ורציפות. אם זו שאלה מורכבת, בקשה לקוד או ידע כללי, ענה באריכות ובפירוט הנדרש כמו עוזר וירטואלי מעולה. 
רק אם הוא מבקש במפורש ניתוח טכני של מניה ספציפית אבל שכח לציין את שם המניה (טיקר) באנגלית, בקש ממנו להקליד את הטיקר.
"""
    return query_gemini(prompt)

def get_ticker_news_summary(ticker_symbol: str) -> str:
    """מושך כותרות חדשות אחרונות מיאהו פייננס ומסכם את הקטליסט המרכזי באמצעות ג'מיני"""
    try:
        t = yf.Ticker(ticker_symbol)
        raw_news = getattr(t, 'news', None)
        if not raw_news:
            return f"📰 לא נמצאו כותרות חדשות עדכניות עבור {ticker_symbol}."

        headlines = []
        for item in raw_news[:4]:
            title = item.get("title")
            publisher = item.get("publisher", "")
            if title:
                headlines.append(f"- {title} ({publisher})")

        if not headlines:
            return f"📰 לא נמצאו כותרות חדשות מובהקות עבור {ticker_symbol}."

        headlines_text = "\n".join(headlines)
        prompt = f"""
להלן הכותרות הכלכליות האחרונות של המניה {ticker_symbol}:
{headlines_text}

תמצת ב-2 עד 3 משפטים בעברית ברורה:
1. מהו הקטליסט או האירוע המרכזי שמופיע בחדשות (דוחות, המלצות אנליסטים, חוזה, תביעה וכו')?
2. האם הנימה הכללית היא חיובית, שלילית או ניטרלית עבור המניה?
הערה לסוחר: זכור שחדשות הן רק רקע; גרף המחיר והווליום הם שקובעים.
"""
        summary = query_gemini(prompt)
        return f"📰 **מבזק קטליסטים וחדשות ({ticker_symbol}):**\n\n{summary}"
    except Exception as e:
        print(f"[News Error] {e}", flush=True)
        return f"לא ניתן היה לאחזר חדשות עבור {ticker_symbol} כרגע."

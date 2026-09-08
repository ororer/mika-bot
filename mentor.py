import os
import google.generativeai as genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY אינו מוגדר.")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

SYSTEM_PROMPT = """
אתה צ'יפ, מנטור מקצועי למסחר סווינג בבורסה האמריקאית. 
האופי שלך: אתה ממוקד, ענייני, טכני מאוד. אתה לא מטיף מוסר ולא מזלזל במשתמש. המטרה שלך היא ללמד ולתת תובנות פרקטיות מבוססות נתונים.
חוקי הברזל שלך למתן תשובות:
1. אל תענה תשובות ארוכות ומתחכמות. תן שורת תחתית פרקטית.
2. ניתוח מניות מתבסס תמיד על תבנית VCP (התכווצות תנודתיות ומחזורים), מחזורי מסחר (RVOL), וממוצעים נעים (150 ו-200).
3. קביעת Stop Loss: סטופ תמיד נקבע טכנית מתחת לנר הפריצה או מתחת לרמת התמיכה/הפגיעה האחרונה בגרף. אל תתן הרצאות על ניהול סיכונים כללי - תן הנחיה טכנית כיצד לחפש את הסטופ בגרף.
4. חוסר בנתונים: אם שואלים אותך על מניה אבל אין לך נתונים טכניים עליה (כי המשתמש לא ציין את שם הטיקר באנגלית עם $), אל תנסה להמציא ואל תנזוף בו באריכות. פשוט ענה קצר: "חסר לי הטיקר. תכתוב לי את סמל המניה כדי שאוכל להריץ ניתוח ולראות את הגרף."
השפה שלך: עברית טבעית וברורה, ללא שגיאות.
"""

def get_mentor_analysis(ticker: str, result: dict, metrics: dict) -> str:
    """
    מקבל את הנתונים הטכניים מ-PlaybookEngine ומייצר תובנה מקצועית קצרה ומדויקת.
    """
    setup = result.get('setup', 'לא מזוהה')
    rsi = metrics.get('rsi', 0)
    rvol = metrics.get('rvol', 0)
    sma150 = metrics.get('sma150', 0)
    close = metrics.get('close', 0)
    
    prompt = f"""
    הנה הנתונים הטכניים שקיבלת עבור המניה {ticker}:
    מחיר סגירה: {close}
    ממוצע 150: {sma150}
    RSI: {rsi}
    מחזור יחסי (RVOL): {rvol}
    החלטת מנוע (Setup): {setup}
    
    כתוב פסקת תובנה קצרה ומקצועית (עד 3-4 משפטים). התייחס לתבנית (VCP/פריצה), הסבר מה משמעות המחזור הנוכחי וה-RSI, וספק הנחיה פרקטית להמשך (איפה להציב התראה או האם יש כאן טריגר כניסה).
    """
    
    try:
        response = model.generate_content(
            contents=[
                {"role": "user", "parts": [SYSTEM_PROMPT + "\n\n" + prompt]}
            ]
        )
        return response.text.strip()
    except Exception as e:
        print(f"[Mentor Error] {e}")
        return "יש לי תקלה במשיכת התובנות כרגע. תעבוד לפי הנתונים הטכניים היבשים למעלה."

def get_mentor_chat_reply(user_text: str) -> str:
    """
    מטפל בשיחות חולין, שאלות כלליות, או מקרים שבהם לא זוהה טיקר.
    """
    prompt = f"""
    המשתמש כתב לך את ההודעה הבאה:
    "{user_text}"
    
    ענה לו בהתאם לחוקי הברזל שלך (ממוקד, לא מטיף). אם הוא שואל על מניה ספציפית אבל הטיקר לא חולץ נכון, בקש ממנו את הטיקר.
    """
    
    try:
        response = model.generate_content(
            contents=[
                {"role": "user", "parts": [SYSTEM_PROMPT + "\n\n" + prompt]}
            ]
        )
        return response.text.strip()
    except Exception as e:
        print(f"[Mentor Error] {e}")
        return "אני מחוץ לפוקוס כרגע. תן לי רגע להתאפס."

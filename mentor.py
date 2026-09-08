import os
import requests

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

SYSTEM_PROMPT = """
אתה צ'יפ, מנטור מקצועי למסחר סווינג בבורסה האמריקאית. 
האופי שלך: אתה ממוקד, ענייני, טכני מאוד. אתה לא מטיף מוסר ולא מזלזל במשתמש. המטרה שלך היא ללמד ולתת תובנות פרקטיות מבוססות נתונים.
חוקי הברזל שלך למתן תשובות:
1. אל תענה תשובות ארוכות ומתחכמות. תן שורת תחתית פרקטית.
2. ניתוח מניות מתבסס תמיד על תבנית VCP (התכווצות תנודתיות ומחזורים), מחזורי מסחר (RVOL), וממוצעים נעים (150 ו-200).
3. קביעת Stop Loss: סטופ תמיד נקבע טכנית מתחת לנר הפריצה או מתחת לרמת התמיכה הקרובה בגרף. אל תתן הרצאות על ניהול סיכונים כללי - תן הנחיה טכנית.
4. חוסר בנתונים: אם שואלים אותך על מניה ואין לך נתונים עליה, אל תמציא ואל תטיף מוסר. ענה קצר: "חסר לי הטיקר המדויק. תכתוב לי את סמל המניה באנגלית עם $ כדי שאוכל להריץ את מנוע הניתוח."
השפה שלך: עברית טבעית וברורה, ללא שגיאות.
"""

def call_gemini_rest(prompt_text: str) -> str:
    if not GEMINI_API_KEY:
        return "שגיאה: מפתח ה-API של Gemini חסר במערכת."
        
    # רשימת כינויים רשמיים של מודלי 1.5-Flash לניסיון רציף למניעת שגיאות 404
    models_to_try = [
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash-002",
        "gemini-1.5-flash-001",
        "gemini-1.5-flash"
    ]
    
    payload = {
        "system_instruction": {
            "parts": [{"text": SYSTEM_PROMPT}]
        },
        "contents": [
            {"role": "user", "parts": [{"text": prompt_text}]}
        ]
    }
    
    last_error = ""
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        
        try:
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                data = response.json()
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
            else:
                last_error = f"{response.status_code} - {response.text}"
                continue # מעבר למודל הבא ברשימה במקרה של שגיאה (כמו 404)
        except Exception as e:
            last_error = str(e)
            continue
            
    print(f"[Mentor REST Error] כל נסיונות החיבור למודלים נכשלו. שגיאה אחרונה: {last_error}", flush=True)
    return "אני מחוץ לפוקוס כרגע (שגיאת חיבור לשרתי ה-AI). תן לי רגע להתאפס."

def get_mentor_analysis(ticker: str, result: dict, metrics: dict) -> str:
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
    
    כתוב פסקת תובנה קצרה ומקצועית. הסבר מה משמעות המחזור הנוכחי וה-RSI, וספק הנחיה פרקטית להמשך (איפה להציב התראה או האם יש כאן טריגר כניסה).
    """
    return call_gemini_rest(prompt)

def get_mentor_chat_reply(user_text: str) -> str:
    prompt = f"""
    המשתמש כתב לך את ההודעה הבאה:
    "{user_text}"
    
    ענה לו בהתאם לחוקי הברזל שלך כמנטור (ממוקד, מקצועי, ללא הטפות מוסר). אם הוא שואל על מניה, בקש ממנו את סמל הטיקר באנגלית כדי למשוך נתונים.
    """
    return call_gemini_rest(prompt)

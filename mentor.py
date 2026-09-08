import os
from datetime import datetime
import pytz
import google.generativeai as genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def get_current_market_context() -> str:
    tz_ny = pytz.timezone("America/New_York")
    now_ny = datetime.now(tz_ny)
    day_name = now_ny.strftime("%A")
    date_str = now_ny.strftime("%Y-%m-%d")
    time_str = now_ny.strftime("%H:%M")
    return f"תאריך היום (שעון ניו יורק): {date_str} ({day_name}), שעה: {time_str}"

def call_gemini(prompt: str) -> str:
    if not GEMINI_API_KEY:
        return "מפתח ה-API של Gemini אינו מוגדר בסביבה."
    
    try:
        available = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available.append(m.name)
        
        if not available:
            return "גוגל לא החזיר אף מודל שתומך ב-generateContent עבור המפתח הזה."

        return "רשימת המודלים הפעילים בחשבון שלך:\n\n" + "\n".join(available)
    except Exception as e:
        return f"שגיאה בשליפת רשימת המודלים מגוגל: {e}"

def get_mentor_analysis(ticker: str, result: dict, last_price: float, rsi: float, sma150: float) -> str:
    return call_gemini("test")

def get_mentor_chat_reply(user_message: str) -> str:
    return call_gemini(user_message)

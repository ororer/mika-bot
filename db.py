import os
from datetime import date
from typing import List, Dict, Optional
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

_supabase: Optional[Client] = None

def get_supabase_client() -> Optional[Client]:
    """מחזיר מופע של לקוח Supabase אם המפתחות מוגדרים."""
    global _supabase
    if _supabase is None and SUPABASE_URL and SUPABASE_KEY:
        _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase

def get_active_trades() -> List[Dict]:
    """שולף את כל העסקאות הפעילות מטבלת chip_active_trades."""
    client = get_supabase_client()
    if not client:
        return []
    try:
        response = client.table("chip_active_trades").select("*").order("created_at", desc=False).execute()
        return response.data or []
    except Exception as e:
        print(f"[DB ERROR] Failed to fetch active trades: {e}")
        return []

def add_active_trade(ticker: str, entry_price: float, stop_loss: float, target_price: Optional[float] = None, setup_type: str = "Breakout", notes: str = "") -> bool:
    """מוסיף עסקה פעילה חדשה."""
    client = get_supabase_client()
    if not client:
        return False
    try:
        data = {
            "ticker": ticker.upper(),
            "entry_date": str(date.today()),
            "entry_price": float(entry_price),
            "stop_loss": float(stop_loss),
            "target_price": float(target_price) if target_price else None,
            "setup_type": setup_type,
            "notes": notes
        }
        client.table("chip_active_trades").insert(data).execute()
        return True
    except Exception as e:
        print(f"[DB ERROR] Failed to add active trade: {e}")
        return False

def close_trade(ticker: str, exit_price: float, exit_reason: str = "Target Hit", mentor_takeaways: str = "") -> bool:
    """מעביר עסקה מטבלת העסקאות הפעילות לטבלת ההיסטוריה תוך חישוב PnL."""
    client = get_supabase_client()
    if not client:
        return False
    try:
        # 1. שליפת פרטי העסקה הקיימת
        response = client.table("chip_active_trades").select("*").eq("ticker", ticker.upper()).execute()
        if not response.data:
            print(f"[DB WARNING] No active trade found for {ticker}")
            return False

        trade = response.data[0]
        entry_price = float(trade["entry_price"])
        exit_price_val = float(exit_price)
        pnl_pct = round(((exit_price_val - entry_price) / entry_price) * 100, 2)
        pnl_amount = round(exit_price_val - entry_price, 2)

        # 2. הוספה להיסטוריית עסקאות
        history_data = {
            "ticker": trade["ticker"],
            "entry_date": trade["entry_date"],
            "entry_price": entry_price,
            "exit_date": str(date.today()),
            "exit_price": exit_price_val,
            "pnl_pct": pnl_pct,
            "pnl_amount": pnl_amount,
            "exit_reason": exit_reason,
            "mentor_takeaways": mentor_takeaways
        }
        client.table("chip_trade_history").insert(history_data).execute()

        # 3. מחיקה מהעסקאות הפעילות
        client.table("chip_active_trades").delete().eq("ticker", ticker.upper()).execute()
        return True
    except Exception as e:
        print(f"[DB ERROR] Failed to close trade: {e}")
        return False

def get_trade_history(limit: int = 10) -> List[Dict]:
    """שולף עסקאות אחרונות שנסגרו."""
    client = get_supabase_client()
    if not client:
        return []
    try:
        response = client.table("chip_trade_history").select("*").order("exit_date", desc=True).limit(limit).execute()
        return response.data or []
    except Exception as e:
        print(f"[DB ERROR] Failed to fetch trade history: {e}")
        return []

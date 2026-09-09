import pandas as pd
import numpy as np

class PlaybookEngine:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self._calculate_indicators()

    def _calculate_indicators(self):
        if isinstance(self.df.columns, pd.MultiIndex):
            self.df.columns = [col[0] for col in self.df.columns]

        # חישוב ממוצע 20 שהוספנו
        self.df['SMA_20'] = self.df['Close'].rolling(window=20, min_periods=20).mean()
        
        self.df['SMA_50'] = self.df['Close'].rolling(window=50, min_periods=50).mean()
        self.df['SMA_150'] = self.df['Close'].rolling(window=150, min_periods=150).mean()
        self.df['SMA_200'] = self.df['Close'].rolling(window=200, min_periods=200).mean()

        self.df['EMA_10'] = self.df['Close'].ewm(span=10, adjust=False).mean()
        self.df['EMA_21'] = self.df['Close'].ewm(span=21, adjust=False).mean()

        delta = self.df['Close'].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.rolling(window=14, min_periods=14).mean()
        avg_loss = loss.rolling(window=14, min_periods=14).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100.0 - (100.0 / (1.0 + rs))
        self.df['RSI_14'] = rsi.fillna(100.0 * (avg_gain > 0))

        high_low = self.df['High'] - self.df['Low']
        high_close = (self.df['High'] - self.df['Close'].shift(1)).abs()
        low_close = (self.df['Low'] - self.df['Close'].shift(1)).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        self.df['ATR_14'] = true_range.rolling(window=14, min_periods=14).mean()

        if 'Volume' in self.df.columns:
            vol_sma20 = self.df['Volume'].rolling(window=20, min_periods=20).mean()
            self.df['RVOL'] = (self.df['Volume'] / vol_sma20.replace(0, np.nan)).fillna(1.0)
        else:
            self.df['RVOL'] = 1.0

        ema12 = self.df['Close'].ewm(span=12, adjust=False).mean()
        ema26 = self.df['Close'].ewm(span=26, adjust=False).mean()
        self.df['MACD'] = ema12 - ema26
        self.df['MACD_Signal'] = self.df['MACD'].ewm(span=9, adjust=False).mean()
        self.df['MACD_Hist'] = self.df['MACD'] - self.df['MACD_Signal']

    def _detect_vcp(self) -> bool:
        if len(self.df) < 15:
            return False
        ranges = (self.df['High'] - self.df['Low']).tail(10).values
        first_half_avg = np.mean(ranges[:5])
        second_half_avg = np.mean(ranges[5:])
        return second_half_avg < (first_half_avg * 0.70)

    def _check_market_structure(self) -> str:
        if len(self.df) < 25:
            return "נתונים חסרים"
        recent = self.df.tail(20)
        highs = recent['High'].values
        lows = recent['Low'].values
        
        min_first = np.min(lows[:10])
        min_second = np.min(lows[10:])
        max_first = np.max(highs[:10])
        max_second = np.max(highs[10:])
        
        if min_second > min_first and max_second > max_first:
            return "מבנה עולה (Higher Highs & Higher Lows)"
        elif min_second < min_first and max_second < max_first:
            return "מבנה יורד (Lower Highs & Lower Lows)"
        return "מבנה מדשדש / ללא כיוון מובהק"

    def _detect_divergence(self) -> str:
        if len(self.df) < 20:
            return "ללא"
        recent = self.df.tail(14)
        price_start, price_end = recent['Close'].iloc[0], recent['Close'].iloc[-1]
        rsi_start, rsi_end = recent['RSI_14'].iloc[0], recent['RSI_14'].iloc[-1]

        if price_end < price_start and rsi_end > rsi_start and rsi_end < 45:
            return "סטייה שורית ב-RSI (Bullish Divergence)"
        if price_end > price_start and rsi_end < rsi_start and rsi_end > 65:
            return "סטייה דובית ב-RSI (Bearish Divergence)"
        return "ללא"

    def evaluate(self) -> dict:
        if len(self.df) < 155 or pd.isna(self.df['SMA_150'].iloc[-1]):
            return {
                "status": "WAIT",
                "message": "אין מספיק נרות מסחר לחישוב ממוצע 150 מלא.",
                "setup": "נתונים חסרים",
                "stop_loss": None,
                "metrics": {}
            }

        curr = self.df.iloc[-1]
        prev = self.df.iloc[-2]

        close = float(curr['Close'])
        
        # חילוץ ממוצע 20
        sma20 = float(curr['SMA_20']) if not pd.isna(curr['SMA_20']) else close
        
        sma50 = float(curr['SMA_50']) if not pd.isna(curr['SMA_50']) else close
        sma150 = float(curr['SMA_150'])
        sma200 = float(curr['SMA_200']) if not pd.isna(curr['SMA_200']) else sma150
        ema10 = float(curr['EMA_10'])
        ema21 = float(curr['EMA_21'])
        rsi = float(curr['RSI_14']) if not pd.isna(curr['RSI_14']) else 50.0
        atr = float(curr['ATR_14']) if not pd.isna(curr['ATR_14']) else 0.0
        rvol = float(curr['RVOL']) if not pd.isna(curr['RVOL']) else 1.0

        is_vcp = self._detect_vcp()
        structure = self._check_market_structure()
        divergence = self._detect_divergence()

        # הוספת sma20 למילון שמועבר ל-Gemini
        metrics = {
            "close": close,
            "sma20": sma20,
            "sma50": sma50,
            "sma150": sma150,
            "sma200": sma200,
            "ema10": ema10,
            "ema21": ema21,
            "rsi": rsi,
            "atr": atr,
            "rvol": rvol,
            "is_vcp": is_vcp,
            "structure": structure,
            "divergence": divergence
        }

        if close < sma150:
            return {
                "status": "AVOID",
                "message": "המניה נסחרת מתחת לממוצע נע 150. שום דבר טוב לא קורה מתחת לממוצע 150 – לא נוגעים בסכין נופלת.",
                "setup": "סכין נופלת",
                "stop_loss": None,
                "metrics": metrics
            }

        if rsi > 70:
            return {
                "status": "WAIT",
                "message": "RSI מעל 70 – המניה מתוחה מדי לקנייה חדשה. ממתינים להתכנסות או פולבק, לא רודפים.",
                "setup": "קניית יתר (Overbought)",
                "stop_loss": None,
                "metrics": metrics
            }

        prev_open = float(prev['Open'])
        prev_close = float(prev['Close'])
        prev_low = float(prev['Low'])
        prev_high = float(prev['High'])
        curr_close = float(curr['Close'])

        body = abs(prev_close - prev_open)
        lower_shadow = min(prev_open, prev_close) - prev_low
        is_hammer = (prev_close >= prev_open) and (lower_shadow >= 2 * body) and (body > 0)
        is_confirmed = curr_close > prev_high

        if is_hammer and is_confirmed:
            stop_loss = prev_low * 0.995
            vol_note = "עם מחזור חריג תומך" if rvol >= 1.2 else "מחזור מסחר ממוצע"
            return {
                "status": "BUY",
                "message": f"זוהה נר פטיש עם יום אישור המשכיות (Follow-Through) מעל ממוצע 150 ({vol_note}).",
                "setup": "Hammer + Confirmation",
                "stop_loss": f"{stop_loss:.2f}$",
                "metrics": metrics
            }

        if is_vcp and close > ema10 and rvol >= 1.3:
            stop_loss = ema21 * 0.99
            return {
                "status": "BUY",
                "message": f"דחיסת תנודתיות (VCP) עם פריצה בנפח מסחר חריג (RVOL: {rvol:.2f}). מומנטום חזק מעל EMA 10.",
                "setup": "VCP Breakout",
                "stop_loss": f"{stop_loss:.2f}$",
                "metrics": metrics
            }

        return {
            "status": "WAIT",
            "message": "המניה במגמה חיובית מעל ממוצע 150, אך אין כרגע טריגר היפוך או דחיסה מושלמת להנחת סטופ-לוס. יושבים על הגדר בסבלנות.",
            "setup": "אין תבנית מובהקת",
            "stop_loss": None,
            "metrics": metrics
        }

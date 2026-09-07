import pandas as pd
import numpy as np

class PlaybookEngine:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self._calculate_indicators()

    def _calculate_indicators(self):
        if isinstance(self.df.columns, pd.MultiIndex):
            self.df.columns = [col[0] for col in self.df.columns]

        self.df['SMA_50'] = self.df['Close'].rolling(window=50, min_periods=50).mean()
        self.df['SMA_150'] = self.df['Close'].rolling(window=150, min_periods=150).mean()
        self.df['SMA_200'] = self.df['Close'].rolling(window=200, min_periods=200).mean()

        delta = self.df['Close'].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)

        avg_gain = gain.rolling(window=14, min_periods=14).mean()
        avg_loss = loss.rolling(window=14, min_periods=14).mean()

        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100.0 - (100.0 / (1.0 + rs))
        rsi = rsi.fillna(100.0 * (avg_gain > 0))
        self.df['RSI_14'] = rsi

    def evaluate(self) -> dict:
        if len(self.df) < 155 or pd.isna(self.df['SMA_150'].iloc[-1]):
            return {
                "status": "WAIT",
                "message": "אין מספיק נרות מסחר לחישוב ממוצע 150 מלא.",
                "setup": "נתונים חסרים",
                "stop_loss": None
            }

        curr = self.df.iloc[-1]
        prev = self.df.iloc[-2]

        close = float(curr['Close'])
        sma150 = float(curr['SMA_150'])
        rsi = float(curr['RSI_14']) if not pd.isna(curr['RSI_14']) else 50.0

        if close < sma150:
            return {
                "status": "AVOID",
                "message": "המניה נסחרת מתחת לממוצע נע 150. שום דבר טוב לא קורה מתחת לממוצע 150 – לא נוגעים בסכין נופלת.",
                "setup": "סכין נופלת",
                "stop_loss": None
            }

        if rsi > 70:
            return {
                "status": "WAIT",
                "message": "RSI מעל 70 – המניה מתוחה מדי לקנייה חדשה. ממתינים להתכנסות או פולבק, לא רודפים.",
                "setup": "קניית יתר (Overbought)",
                "stop_loss": None
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
            return {
                "status": "BUY",
                "message": "זוהה נר פטיש עם יום אישור המשכיות (Follow-Through) מעל ממוצע 150. סט-אפ איכותי לפי הספר.",
                "setup": "Hammer + Confirmation",
                "stop_loss": f"{stop_loss:.2f}$"
            }

        return {
            "status": "WAIT",
            "message": "המניה במגמה חיובית מעל ממוצע 150, אך אין כרגע טריגר היפוך או שפל מוגדר להנחת סטופ-לוס. ממתינים בסבלנות.",
            "setup": "אין תבנית מובהקת",
            "stop_loss": None
        }

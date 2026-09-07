import pandas as pd
import numpy as np

class PlaybookEngine:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self._calculate_indicators()

    def _calculate_indicators(self):
        # ממוצעים נעים פשוטים (SMA)
        for period in [20, 50, 100, 150, 200]:
            self.df[f"SMA_{period}"] = self.df["Close"].rolling(window=period).mean()

        # שיפוע SMA 150 (השוואה 5 ימים לאחור)
        self.df["SMA_150_Slope"] = (self.df["SMA_150"] - self.df["SMA_150"].shift(5)) / 5

        # חישוב RSI 14
        delta = self.df["Close"].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        self.df["RSI_14"] = 100 - (100 / (1 + rs))

        # הגדרת נר פטיש (Hammer)
        body = abs(self.df["Close"] - self.df["Open"])
        total_range = self.df["High"] - self.df["Low"]
        lower_wick = self.df[["Open", "Close"]].min(axis=1) - self.df["Low"]
        upper_wick = self.df["High"] - self.df[["Open", "Close"]].max(axis=1)

        self.df["Is_Hammer"] = (
            (lower_wick >= 2 * body) & 
            (upper_wick <= 0.15 * total_range) & 
            (self.df[["Open", "Close"]].min(axis=1) >= (self.df["Low"] + 0.6 * total_range))
        )

    def evaluate(self) -> dict:
        curr = self.df.iloc[-1]
        prev = self.df.iloc[-2]

        # 1. בדיקת פסילה: סכין נופלת
        if curr["Close"] < curr["SMA_150"] and curr["SMA_150_Slope"] < 0:
            return {
                "status": "REJECTED",
                "message": "סכין נופלת: המחיר מתחת ל-SMA 150 והממוצע בירידה."
            }

        # 2. בדיקת פסילה: מתיחת יתר (RSI מעל 70)
        if curr["RSI_14"] > 70:
            return {
                "status": "REJECTED",
                "message": "RSI מעל 70 - קנייה בפרמיה מוגזמת."
            }

        # 3. טריגר: פטיש מאתמול + אישור המשכיות היום
        if prev["Is_Hammer"] and curr["Close"] > prev["Close"]:
            return {
                "status": "BUY_SIGNAL",
                "setup": "Hammer Follow-Through",
                "stop_loss": round(float(prev["Low"]), 2),
                "message": "אושר היפוך פטיש עם יום המשכיות ירוק."
            }

        # 4. טריגר: קניית ערך סביב SMA 150
        diff_pct = (curr["Close"] - curr["SMA_150"]) / curr["SMA_150"] * 100
        if 0 <= diff_pct <= 2.0 and curr["SMA_150_Slope"] >= 0:
            return {
                "status": "BUY_SIGNAL",
                "setup": "SMA 150 Value Bounce",
                "stop_loss": round(float(curr["SMA_150"] * 0.985), 2),
                "message": f"המחיר בקרבה של {diff_pct:.2f}% מעל ממוצע 150 עולה."
            }

        return {
            "status": "WAIT",
            "message": "תנאי סף תקינים, אך אין טריגר כניסה פעיל כרגע."
        }

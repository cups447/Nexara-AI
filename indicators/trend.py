import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple
from config.settings import settings
from utils.logger import logger


class TrendIndicators:

    @staticmethod
    def ema(series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()

    @staticmethod
    def calculate_emas(df: pd.DataFrame) -> pd.DataFrame:
        try:
            df["ema_20"] = TrendIndicators.ema(df["close"], settings.EMA_FAST)
            df["ema_50"] = TrendIndicators.ema(df["close"], settings.EMA_MID)
            df["ema_100"] = TrendIndicators.ema(df["close"], settings.EMA_SLOW)
            df["ema_200"] = TrendIndicators.ema(df["close"], settings.EMA_TREND)
            return df
        except Exception as e:
            logger.error(f"Error calculating EMAs: {e}")
            return df

    @staticmethod
    def macd(
        series: pd.Series,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        try:
            ema_fast = series.ewm(span=fast, adjust=False).mean()
            ema_slow = series.ewm(span=slow, adjust=False).mean()
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=signal, adjust=False).mean()
            histogram = macd_line - signal_line
            return macd_line, signal_line, histogram
        except Exception as e:
            logger.error(f"Error calculating MACD: {e}")
            return pd.Series(), pd.Series(), pd.Series()

    @staticmethod
    def calculate_macd(df: pd.DataFrame) -> pd.DataFrame:
        try:
            macd_line, signal_line, histogram = TrendIndicators.macd(
                df["close"],
                settings.MACD_FAST,
                settings.MACD_SLOW,
                settings.MACD_SIGNAL,
            )
            df["macd"] = macd_line
            df["macd_signal"] = signal_line
            df["macd_hist"] = histogram
            return df
        except Exception as e:
            logger.error(f"Error calculating MACD dataframe: {e}")
            return df

    @staticmethod
    def adx(
        df: pd.DataFrame,
        period: int = 14,
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        try:
            high = df["high"]
            low = df["low"]
            close = df["close"]

            plus_dm = high.diff()
            minus_dm = low.diff().abs()

            plus_dm = plus_dm.where(
                (plus_dm > minus_dm) & (plus_dm > 0), 0.0
            )
            minus_dm = minus_dm.where(
                (minus_dm > plus_dm.abs()) & (minus_dm > 0), 0.0
            )

            tr1 = high - low
            tr2 = (high - close.shift()).abs()
            tr3 = (low - close.shift()).abs()
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

            atr = true_range.ewm(span=period, adjust=False).mean()
            plus_di = 100 * (plus_dm.ewm(span=period, adjust=False).mean() / atr)
            minus_di = 100 * (minus_dm.ewm(span=period, adjust=False).mean() / atr)

            dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
            adx_val = dx.ewm(span=period, adjust=False).mean()

            return adx_val, plus_di, minus_di
        except Exception as e:
            logger.error(f"Error calculating ADX: {e}")
            return pd.Series(), pd.Series(), pd.Series()

    @staticmethod
    def calculate_adx(df: pd.DataFrame) -> pd.DataFrame:
        try:
            adx_val, plus_di, minus_di = TrendIndicators.adx(df, settings.ADX_PERIOD)
            df["adx"] = adx_val
            df["plus_di"] = plus_di
            df["minus_di"] = minus_di
            return df
        except Exception as e:
            logger.error(f"Error calculating ADX dataframe: {e}")
            return df

    @staticmethod
    def supertrend(
        df: pd.DataFrame,
        period: int = 10,
        multiplier: float = 3.0,
    ) -> Tuple[pd.Series, pd.Series]:
        try:
            high = df["high"]
            low = df["low"]
            close = df["close"]

            tr1 = high - low
            tr2 = (high - close.shift()).abs()
            tr3 = (low - close.shift()).abs()
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = true_range.ewm(span=period, adjust=False).mean()

            hl2 = (high + low) / 2
            upper_band = hl2 + multiplier * atr
            lower_band = hl2 - multiplier * atr

            supertrend_vals = pd.Series(index=df.index, dtype=float)
            direction = pd.Series(index=df.index, dtype=float)

            supertrend_vals.iloc[0] = lower_band.iloc[0]
            direction.iloc[0] = 1

            for i in range(1, len(df)):
                prev_st = supertrend_vals.iloc[i - 1]
                prev_dir = direction.iloc[i - 1]
                curr_close = close.iloc[i]
                curr_upper = upper_band.iloc[i]
                curr_lower = lower_band.iloc[i]
                prev_upper = upper_band.iloc[i - 1]
                prev_lower = lower_band.iloc[i - 1]

                curr_lower = max(curr_lower, prev_lower) if curr_close > prev_lower else curr_lower
                curr_upper = min(curr_upper, prev_upper) if curr_close < prev_upper else curr_upper

                if prev_dir == 1:
                    if curr_close < curr_lower:
                        supertrend_vals.iloc[i] = curr_upper
                        direction.iloc[i] = -1
                    else:
                        supertrend_vals.iloc[i] = curr_lower
                        direction.iloc[i] = 1
                else:
                    if curr_close > curr_upper:
                        supertrend_vals.iloc[i] = curr_lower
                        direction.iloc[i] = 1
                    else:
                        supertrend_vals.iloc[i] = curr_upper
                        direction.iloc[i] = -1

            return supertrend_vals, direction
        except Exception as e:
            logger.error(f"Error calculating Supertrend: {e}")
            return pd.Series(), pd.Series()

    @staticmethod
    def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
        try:
            st_vals, st_dir = TrendIndicators.supertrend(
                df,
                settings.SUPERTREND_PERIOD,
                settings.SUPERTREND_MULTIPLIER,
            )
            df["supertrend"] = st_vals
            df["supertrend_dir"] = st_dir
            return df
        except Exception as e:
            logger.error(f"Error calculating Supertrend dataframe: {e}")
            return df

    @staticmethod
    def get_ema_trend(df: pd.DataFrame) -> str:
        try:
            last = df.iloc[-1]
            close = last["close"]
            ema20 = last.get("ema_20", np.nan)
            ema50 = last.get("ema_50", np.nan)
            ema100 = last.get("ema_100", np.nan)
            ema200 = last.get("ema_200", np.nan)

            if pd.isna(ema20) or pd.isna(ema50) or pd.isna(ema200):
                return "NEUTRAL"

            bullish = (
                close > ema20 > ema50 > ema100 > ema200
            )
            bearish = (
                close < ema20 < ema50 < ema100 < ema200
            )

            if bullish:
                return "BULLISH"
            elif bearish:
                return "BEARISH"
            return "NEUTRAL"
        except Exception as e:
            logger.error(f"Error getting EMA trend: {e}")
            return "NEUTRAL"

    @staticmethod
    def get_macd_signal(df: pd.DataFrame) -> Dict[str, Any]:
        try:
            last = df.iloc[-1]
            prev = df.iloc[-2]

            macd = last.get("macd", np.nan)
            signal = last.get("macd_signal", np.nan)
            hist = last.get("macd_hist", np.nan)
            prev_hist = prev.get("macd_hist", np.nan)

            if pd.isna(macd) or pd.isna(signal):
                return {"signal": "NEUTRAL", "bullish": False, "bearish": False}

            bullish_cross = (
                prev.get("macd", 0) < prev.get("macd_signal", 0)
                and macd > signal
            )
            bearish_cross = (
                prev.get("macd", 0) > prev.get("macd_signal", 0)
                and macd < signal
            )
            hist_increasing = hist > prev_hist
            above_zero = macd > 0

            return {
                "signal": "BULLISH" if macd > signal else "BEARISH",
                "bullish": macd > signal,
                "bearish": macd < signal,
                "bullish_cross": bullish_cross,
                "bearish_cross": bearish_cross,
                "histogram_increasing": hist_increasing,
                "above_zero": above_zero,
                "macd": float(macd),
                "signal_line": float(signal),
                "histogram": float(hist),
            }
        except Exception as e:
            logger.error(f"Error getting MACD signal: {e}")
            return {"signal": "NEUTRAL", "bullish": False, "bearish": False}

    @staticmethod
    def get_adx_signal(df: pd.DataFrame) -> Dict[str, Any]:
        try:
            last = df.iloc[-1]
            adx = last.get("adx", np.nan)
            plus_di = last.get("plus_di", np.nan)
            minus_di = last.get("minus_di", np.nan)

            if pd.isna(adx):
                return {"trending": False, "strength": "WEAK", "direction": "NEUTRAL"}

            trending = adx >= settings.ADX_THRESHOLD
            strength = (
                "STRONG" if adx >= 40
                else "MODERATE" if adx >= 25
                else "WEAK"
            )
            direction = (
                "BULLISH" if plus_di > minus_di
                else "BEARISH"
            )

            return {
                "trending": trending,
                "strength": strength,
                "direction": direction,
                "adx": float(adx),
                "plus_di": float(plus_di) if not pd.isna(plus_di) else 0.0,
                "minus_di": float(minus_di) if not pd.isna(minus_di) else 0.0,
            }
        except Exception as e:
            logger.error(f"Error getting ADX signal: {e}")
            return {"trending": False, "strength": "WEAK", "direction": "NEUTRAL"}

    @staticmethod
    def get_supertrend_signal(df: pd.DataFrame) -> Dict[str, Any]:
        try:
            last = df.iloc[-1]
            prev = df.iloc[-2]

            direction = last.get("supertrend_dir", np.nan)
            prev_direction = prev.get("supertrend_dir", np.nan)
            st_val = last.get("supertrend", np.nan)

            if pd.isna(direction):
                return {"bullish": False, "bearish": False, "signal": "NEUTRAL"}

            bullish = direction == 1
            bearish = direction == -1
            just_flipped_bull = bullish and prev_direction == -1
            just_flipped_bear = bearish and prev_direction == 1

            return {
                "bullish": bullish,
                "bearish": bearish,
                "just_flipped_bullish": just_flipped_bull,
                "just_flipped_bearish": just_flipped_bear,
                "signal": "BULLISH" if bullish else "BEARISH",
                "value": float(st_val) if not pd.isna(st_val) else 0.0,
            }
        except Exception as e:
            logger.error(f"Error getting Supertrend signal: {e}")
            return {"bullish": False, "bearish": False, "signal": "NEUTRAL"}

    @staticmethod
    def calculate_all(df: pd.DataFrame) -> pd.DataFrame:
        try:
            df = TrendIndicators.calculate_emas(df)
            df = TrendIndicators.calculate_macd(df)
            df = TrendIndicators.calculate_adx(df)
            df = TrendIndicators.calculate_supertrend(df)
            return df
        except Exception as e:
            logger.error(f"Error calculating all trend indicators: {e}")
            return df

    @staticmethod
    def get_all_signals(df: pd.DataFrame) -> Dict[str, Any]:
        try:
            return {
                "ema_trend": TrendIndicators.get_ema_trend(df),
                "macd": TrendIndicators.get_macd_signal(df),
                "adx": TrendIndicators.get_adx_signal(df),
                "supertrend": TrendIndicators.get_supertrend_signal(df),
            }
        except Exception as e:
            logger.error(f"Error getting all trend signals: {e}")
            return {}


__all__ = ["TrendIndicators"]

import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple
from config.settings import settings
from utils.logger import logger


class VolatilityIndicators:

    @staticmethod
    def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        try:
            high = df["high"]
            low = df["low"]
            close = df["close"]

            tr1 = high - low
            tr2 = (high - close.shift()).abs()
            tr3 = (low - close.shift()).abs()
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr_val = true_range.ewm(span=period, adjust=False).mean()
            return atr_val
        except Exception as e:
            logger.error(f"Error calculating ATR: {e}")
            return pd.Series(dtype=float)

    @staticmethod
    def calculate_atr(df: pd.DataFrame) -> pd.DataFrame:
        try:
            df["atr"] = VolatilityIndicators.atr(df, settings.ATR_PERIOD)
            df["atr_pct"] = (df["atr"] / df["close"]) * 100
            return df
        except Exception as e:
            logger.error(f"Error calculating ATR dataframe: {e}")
            return df

    @staticmethod
    def bollinger_bands(
        series: pd.Series,
        period: int = 20,
        std_dev: float = 2.0,
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        try:
            sma = series.rolling(window=period).mean()
            std = series.rolling(window=period).std()
            upper = sma + (std_dev * std)
            lower = sma - (std_dev * std)
            return upper, sma, lower
        except Exception as e:
            logger.error(f"Error calculating Bollinger Bands: {e}")
            return pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float)

    @staticmethod
    def calculate_bollinger_bands(df: pd.DataFrame) -> pd.DataFrame:
        try:
            upper, mid, lower = VolatilityIndicators.bollinger_bands(
                df["close"],
                settings.BB_PERIOD,
                settings.BB_STD,
            )
            df["bb_upper"] = upper
            df["bb_mid"] = mid
            df["bb_lower"] = lower
            df["bb_width"] = (upper - lower) / mid.replace(0, np.nan)
            df["bb_pct"] = (df["close"] - lower) / (upper - lower).replace(0, np.nan)
            return df
        except Exception as e:
            logger.error(f"Error calculating Bollinger Bands dataframe: {e}")
            return df

    @staticmethod
    def historical_volatility(
        series: pd.Series,
        period: int = 20,
    ) -> pd.Series:
        try:
            log_returns = np.log(series / series.shift(1))
            hv = log_returns.rolling(window=period).std() * np.sqrt(365) * 100
            return hv
        except Exception as e:
            logger.error(f"Error calculating Historical Volatility: {e}")
            return pd.Series(dtype=float)

    @staticmethod
    def calculate_historical_volatility(df: pd.DataFrame) -> pd.DataFrame:
        try:
            df["hv"] = VolatilityIndicators.historical_volatility(df["close"])
            return df
        except Exception as e:
            logger.error(f"Error calculating HV dataframe: {e}")
            return df

    @staticmethod
    def get_atr_signal(df: pd.DataFrame) -> Dict[str, Any]:
        try:
            last = df.iloc[-1]
            atr = last.get("atr", np.nan)
            atr_pct = last.get("atr_pct", np.nan)
            close = last["close"]

            if pd.isna(atr):
                return {
                    "value": 0.0,
                    "pct": 0.0,
                    "volatility": "NORMAL",
                    "sl_distance": 0.0,
                }

            recent_atr = df["atr"].iloc[-20:]
            atr_avg = recent_atr.mean()
            atr_ratio = atr / atr_avg if atr_avg > 0 else 1.0

            if atr_ratio >= 2.0:
                volatility = "EXTREME"
            elif atr_ratio >= 1.5:
                volatility = "HIGH"
            elif atr_ratio <= 0.5:
                volatility = "LOW"
            else:
                volatility = "NORMAL"

            sl_long = close - (atr * settings.ATR_SL_MULTIPLIER)
            sl_short = close + (atr * settings.ATR_SL_MULTIPLIER)
            tp1_long = close + (atr * settings.ATR_TP1_MULTIPLIER)
            tp2_long = close + (atr * settings.ATR_TP2_MULTIPLIER)
            tp3_long = close + (atr * settings.ATR_TP3_MULTIPLIER)
            tp1_short = close - (atr * settings.ATR_TP1_MULTIPLIER)
            tp2_short = close - (atr * settings.ATR_TP2_MULTIPLIER)
            tp3_short = close - (atr * settings.ATR_TP3_MULTIPLIER)

            return {
                "value": float(atr),
                "pct": float(atr_pct) if not pd.isna(atr_pct) else 0.0,
                "ratio": float(atr_ratio),
                "volatility": volatility,
                "sl_distance": float(atr * settings.ATR_SL_MULTIPLIER),
                "levels": {
                    "long": {
                        "sl": float(sl_long),
                        "tp1": float(tp1_long),
                        "tp2": float(tp2_long),
                        "tp3": float(tp3_long),
                    },
                    "short": {
                        "sl": float(sl_short),
                        "tp1": float(tp1_short),
                        "tp2": float(tp2_short),
                        "tp3": float(tp3_short),
                    },
                },
            }
        except Exception as e:
            logger.error(f"Error getting ATR signal: {e}")
            return {"value": 0.0, "pct": 0.0, "volatility": "NORMAL", "sl_distance": 0.0}

    @staticmethod
    def get_bollinger_signal(df: pd.DataFrame) -> Dict[str, Any]:
        try:
            last = df.iloc[-1]
            prev = df.iloc[-2]

            close = last["close"]
            upper = last.get("bb_upper", np.nan)
            mid = last.get("bb_mid", np.nan)
            lower = last.get("bb_lower", np.nan)
            width = last.get("bb_width", np.nan)
            pct = last.get("bb_pct", np.nan)

            prev_close = prev["close"]
            prev_upper = prev.get("bb_upper", np.nan)
            prev_lower = prev.get("bb_lower", np.nan)

            if pd.isna(upper) or pd.isna(lower):
                return {"signal": "NEUTRAL", "squeeze": False, "breakout": False}

            above_upper = close > upper
            below_lower = close < lower
            near_upper = close >= upper * 0.998
            near_lower = close <= lower * 1.002
            above_mid = close > mid

            recent_width = df["bb_width"].iloc[-20:]
            width_avg = recent_width.mean()
            squeeze = width < width_avg * 0.5 if not pd.isna(width) else False

            breakout_up = prev_close <= prev_upper and close > upper
            breakout_down = prev_close >= prev_lower and close < lower

            bounce_up = prev_close <= prev_lower and close > lower
            bounce_down = prev_close >= prev_upper and close < upper

            if breakout_up or bounce_up:
                signal = "BULLISH"
            elif breakout_down or bounce_down:
                signal = "BEARISH"
            elif above_mid:
                signal = "BULLISH"
            else:
                signal = "BEARISH"

            return {
                "signal": signal,
                "upper": float(upper),
                "mid": float(mid),
                "lower": float(lower),
                "width": float(width) if not pd.isna(width) else 0.0,
                "pct": float(pct) if not pd.isna(pct) else 0.5,
                "above_upper": above_upper,
                "below_lower": below_lower,
                "near_upper": near_upper,
                "near_lower": near_lower,
                "squeeze": squeeze,
                "breakout_up": breakout_up,
                "breakout_down": breakout_down,
                "bounce_up": bounce_up,
                "bounce_down": bounce_down,
            }
        except Exception as e:
            logger.error(f"Error getting Bollinger Bands signal: {e}")
            return {"signal": "NEUTRAL", "squeeze": False, "breakout": False}

    @staticmethod
    def get_volatility_regime(df: pd.DataFrame) -> Dict[str, Any]:
        try:
            atr_pct = df["atr_pct"].iloc[-1] if "atr_pct" in df.columns else np.nan
            hv = df["hv"].iloc[-1] if "hv" in df.columns else np.nan
            bb_width = df["bb_width"].iloc[-1] if "bb_width" in df.columns else np.nan

            if pd.isna(atr_pct):
                return {"regime": "UNKNOWN", "tradeable": True}

            if atr_pct >= 5.0:
                regime = "EXTREME"
                tradeable = False
            elif atr_pct >= 3.0:
                regime = "HIGH"
                tradeable = True
            elif atr_pct >= 1.0:
                regime = "NORMAL"
                tradeable = True
            else:
                regime = "LOW"
                tradeable = True

            expanding = False
            contracting = False
            if "bb_width" in df.columns:
                recent_widths = df["bb_width"].iloc[-5:]
                expanding = recent_widths.is_monotonic_increasing
                contracting = recent_widths.is_monotonic_decreasing

            return {
                "regime": regime,
                "tradeable": tradeable,
                "atr_pct": float(atr_pct),
                "hv": float(hv) if not pd.isna(hv) else 0.0,
                "bb_width": float(bb_width) if not pd.isna(bb_width) else 0.0,
                "expanding": expanding,
                "contracting": contracting,
            }
        except Exception as e:
            logger.error(f"Error getting volatility regime: {e}")
            return {"regime": "UNKNOWN", "tradeable": True}

    @staticmethod
    def calculate_all(df: pd.DataFrame) -> pd.DataFrame:
        try:
            df = VolatilityIndicators.calculate_atr(df)
            df = VolatilityIndicators.calculate_bollinger_bands(df)
            df = VolatilityIndicators.calculate_historical_volatility(df)
            return df
        except Exception as e:
            logger.error(f"Error calculating all volatility indicators: {e}")
            return df

    @staticmethod
    def get_all_signals(df: pd.DataFrame) -> Dict[str, Any]:
        try:
            atr_signal = VolatilityIndicators.get_atr_signal(df)
            bb_signal = VolatilityIndicators.get_bollinger_signal(df)
            regime = VolatilityIndicators.get_volatility_regime(df)

            bullish_count = sum([
                bb_signal.get("signal") == "BULLISH",
                bb_signal.get("bounce_up", False),
                bb_signal.get("breakout_up", False),
            ])
            bearish_count = sum([
                bb_signal.get("signal") == "BEARISH",
                bb_signal.get("bounce_down", False),
                bb_signal.get("breakout_down", False),
            ])

            overall = (
                "BULLISH" if bullish_count > bearish_count
                else "BEARISH" if bearish_count > bullish_count
                else "NEUTRAL"
            )

            return {
                "atr": atr_signal,
                "bollinger": bb_signal,
                "regime": regime,
                "overall": overall,
                "bullish_count": bullish_count,
                "bearish_count": bearish_count,
            }
        except Exception as e:
            logger.error(f"Error getting all volatility signals: {e}")
            return {"overall": "NEUTRAL", "regime": {"regime": "UNKNOWN", "tradeable": True}}


__all__ = ["VolatilityIndicators"]

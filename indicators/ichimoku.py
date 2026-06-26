import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple
from utils.logger import logger


class IchimokuIndicators:

    @staticmethod
    def ichimoku(
        df: pd.DataFrame,
        tenkan_period: int = 9,
        kijun_period: int = 26,
        senkou_b_period: int = 52,
        displacement: int = 26,
    ) -> Dict[str, pd.Series]:
        try:
            high = df["high"]
            low = df["low"]
            close = df["close"]

            tenkan_sen = (
                high.rolling(window=tenkan_period).max() +
                low.rolling(window=tenkan_period).min()
            ) / 2

            kijun_sen = (
                high.rolling(window=kijun_period).max() +
                low.rolling(window=kijun_period).min()
            ) / 2

            senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(displacement)

            senkou_span_b = (
                (
                    high.rolling(window=senkou_b_period).max() +
                    low.rolling(window=senkou_b_period).min()
                ) / 2
            ).shift(displacement)

            chikou_span = close.shift(-displacement)

            return {
                "tenkan_sen": tenkan_sen,
                "kijun_sen": kijun_sen,
                "senkou_span_a": senkou_span_a,
                "senkou_span_b": senkou_span_b,
                "chikou_span": chikou_span,
            }
        except Exception as e:
            logger.error(f"Error calculating Ichimoku: {e}")
            return {}

    @staticmethod
    def calculate_ichimoku(df: pd.DataFrame) -> pd.DataFrame:
        try:
            components = IchimokuIndicators.ichimoku(df)
            df["tenkan_sen"] = components.get("tenkan_sen")
            df["kijun_sen"] = components.get("kijun_sen")
            df["senkou_span_a"] = components.get("senkou_span_a")
            df["senkou_span_b"] = components.get("senkou_span_b")
            df["chikou_span"] = components.get("chikou_span")
            return df
        except Exception as e:
            logger.error(f"Error calculating Ichimoku dataframe: {e}")
            return df

    @staticmethod
    def pivot_points(df: pd.DataFrame) -> Dict[str, float]:
        try:
            prev = df.iloc[-2]
            high = float(prev["high"])
            low = float(prev["low"])
            close = float(prev["close"])

            pp = (high + low + close) / 3

            r1 = (2 * pp) - low
            r2 = pp + (high - low)
            r3 = high + 2 * (pp - low)

            s1 = (2 * pp) - high
            s2 = pp - (high - low)
            s3 = low - 2 * (high - pp)

            r4 = r3 + (high - low)
            s4 = s3 - (high - low)

            mid_r1_r2 = (r1 + r2) / 2
            mid_s1_s2 = (s1 + s2) / 2

            return {
                "pp": round(pp, 8),
                "r1": round(r1, 8),
                "r2": round(r2, 8),
                "r3": round(r3, 8),
                "r4": round(r4, 8),
                "s1": round(s1, 8),
                "s2": round(s2, 8),
                "s3": round(s3, 8),
                "s4": round(s4, 8),
                "mid_r1_r2": round(mid_r1_r2, 8),
                "mid_s1_s2": round(mid_s1_s2, 8),
            }
        except Exception as e:
            logger.error(f"Error calculating Pivot Points: {e}")
            return {}

    @staticmethod
    def fibonacci_levels(
        df: pd.DataFrame,
        lookback: int = 50,
    ) -> Dict[str, float]:
        try:
            recent = df.iloc[-lookback:]
            swing_high = float(recent["high"].max())
            swing_low = float(recent["low"].min())
            diff = swing_high - swing_low

            if diff == 0:
                return {}

            fib_ratios = {
                "0.0": 0.0,
                "0.236": 0.236,
                "0.382": 0.382,
                "0.5": 0.5,
                "0.618": 0.618,
                "0.705": 0.705,
                "0.786": 0.786,
                "0.886": 0.886,
                "1.0": 1.0,
                "1.272": 1.272,
                "1.414": 1.414,
                "1.618": 1.618,
                "2.0": 2.0,
                "2.618": 2.618,
            }

            levels = {}
            for name, ratio in fib_ratios.items():
                retracement = swing_high - (diff * ratio)
                levels[f"fib_{name}"] = round(retracement, 8)

            levels["swing_high"] = round(swing_high, 8)
            levels["swing_low"] = round(swing_low, 8)

            return levels
        except Exception as e:
            logger.error(f"Error calculating Fibonacci levels: {e}")
            return {}

    @staticmethod
    def get_ichimoku_signal(df: pd.DataFrame) -> Dict[str, Any]:
        try:
            last = df.iloc[-1]
            close = last["close"]

            tenkan = last.get("tenkan_sen", np.nan)
            kijun = last.get("kijun_sen", np.nan)
            span_a = last.get("senkou_span_a", np.nan)
            span_b = last.get("senkou_span_b", np.nan)

            if pd.isna(tenkan) or pd.isna(kijun) or pd.isna(span_a) or pd.isna(span_b):
                return {"signal": "NEUTRAL", "above_cloud": False, "below_cloud": False}

            cloud_top = max(span_a, span_b)
            cloud_bottom = min(span_a, span_b)

            above_cloud = close > cloud_top
            below_cloud = close < cloud_bottom
            in_cloud = cloud_bottom <= close <= cloud_top

            bullish_cloud = span_a > span_b
            bearish_cloud = span_a < span_b

            tk_cross_bull = tenkan > kijun
            tk_cross_bear = tenkan < kijun

            prev = df.iloc[-2]
            prev_tenkan = prev.get("tenkan_sen", np.nan)
            prev_kijun = prev.get("kijun_sen", np.nan)
            golden_cross = (
                not pd.isna(prev_tenkan) and
                not pd.isna(prev_kijun) and
                prev_tenkan <= prev_kijun and
                tenkan > kijun
            )
            dead_cross = (
                not pd.isna(prev_tenkan) and
                not pd.isna(prev_kijun) and
                prev_tenkan >= prev_kijun and
                tenkan < kijun
            )

            bullish_signals = sum([
                above_cloud,
                tk_cross_bull,
                bullish_cloud,
                golden_cross,
            ])
            bearish_signals = sum([
                below_cloud,
                tk_cross_bear,
                bearish_cloud,
                dead_cross,
            ])

            if bullish_signals >= 3:
                signal = "STRONG_BULLISH"
            elif bullish_signals >= 2:
                signal = "BULLISH"
            elif bearish_signals >= 3:
                signal = "STRONG_BEARISH"
            elif bearish_signals >= 2:
                signal = "BEARISH"
            else:
                signal = "NEUTRAL"

            return {
                "signal": signal,
                "above_cloud": above_cloud,
                "below_cloud": below_cloud,
                "in_cloud": in_cloud,
                "bullish_cloud": bullish_cloud,
                "bearish_cloud": bearish_cloud,
                "tk_cross_bullish": tk_cross_bull,
                "tk_cross_bearish": tk_cross_bear,
                "golden_cross": golden_cross,
                "dead_cross": dead_cross,
                "tenkan": float(tenkan),
                "kijun": float(kijun),
                "span_a": float(span_a),
                "span_b": float(span_b),
                "cloud_top": float(cloud_top),
                "cloud_bottom": float(cloud_bottom),
            }
        except Exception as e:
            logger.error(f"Error getting Ichimoku signal: {e}")
            return {"signal": "NEUTRAL", "above_cloud": False, "below_cloud": False}

    @staticmethod
    def get_pivot_signal(
        df: pd.DataFrame,
        pivots: Dict[str, float],
    ) -> Dict[str, Any]:
        try:
            if not pivots:
                return {"signal": "NEUTRAL", "nearest_level": "pp", "nearest_value": 0.0}

            close = float(df.iloc[-1]["close"])
            pp = pivots.get("pp", close)

            levels = {
                "r4": pivots.get("r4", 0),
                "r3": pivots.get("r3", 0),
                "r2": pivots.get("r2", 0),
                "r1": pivots.get("r1", 0),
                "pp": pp,
                "s1": pivots.get("s1", 0),
                "s2": pivots.get("s2", 0),
                "s3": pivots.get("s3", 0),
                "s4": pivots.get("s4", 0),
            }

            nearest_level = min(levels.items(), key=lambda x: abs(close - x[1]))
            nearest_name = nearest_level[0]
            nearest_val = nearest_level[1]

            distance_pct = abs(close - nearest_val) / nearest_val * 100 if nearest_val != 0 else 0

            above_pp = close > pp
            near_resistance = nearest_name.startswith("r") and distance_pct < 0.5
            near_support = nearest_name.startswith("s") and distance_pct < 0.5
            near_pp = nearest_name == "pp" and distance_pct < 0.3

            signal = "BULLISH" if above_pp else "BEARISH"

            return {
                "signal": signal,
                "above_pp": above_pp,
                "pp": float(pp),
                "nearest_level": nearest_name,
                "nearest_value": float(nearest_val),
                "distance_pct": float(distance_pct),
                "near_resistance": near_resistance,
                "near_support": near_support,
                "near_pp": near_pp,
                "levels": {k: float(v) for k, v in levels.items()},
            }
        except Exception as e:
            logger.error(f"Error getting Pivot signal: {e}")
            return {"signal": "NEUTRAL", "nearest_level": "pp", "nearest_value": 0.0}

    @staticmethod
    def get_fibonacci_signal(
        df: pd.DataFrame,
        fib_levels: Dict[str, float],
    ) -> Dict[str, Any]:
        try:
            if not fib_levels:
                return {"signal": "NEUTRAL", "nearest_level": "fib_0.5", "nearest_value": 0.0}

            close = float(df.iloc[-1]["close"])
            swing_high = fib_levels.get("swing_high", close)
            swing_low = fib_levels.get("swing_low", close)

            key_levels = {
                k: v for k, v in fib_levels.items()
                if k not in ("swing_high", "swing_low")
            }

            nearest = min(key_levels.items(), key=lambda x: abs(close - x[1]))
            nearest_name = nearest[0]
            nearest_val = nearest[1]

            distance_pct = abs(close - nearest_val) / nearest_val * 100 if nearest_val != 0 else 0
            near_level = distance_pct < 0.5

            is_retracement = swing_low <= close <= swing_high
            at_golden_zone = (
                fib_levels.get("fib_0.618", 0) <= close <= fib_levels.get("fib_0.5", 0)
                or fib_levels.get("fib_0.5", 0) <= close <= fib_levels.get("fib_0.618", 0)
            )

            at_deep_retracement = close <= fib_levels.get("fib_0.786", float("inf"))

            above_50 = close > fib_levels.get("fib_0.5", close)
            signal = "BULLISH" if above_50 else "BEARISH"

            return {
                "signal": signal,
                "nearest_level": nearest_name,
                "nearest_value": float(nearest_val),
                "distance_pct": float(distance_pct),
                "near_level": near_level,
                "at_golden_zone": at_golden_zone,
                "at_deep_retracement": at_deep_retracement,
                "is_retracement": is_retracement,
                "swing_high": float(swing_high),
                "swing_low": float(swing_low),
                "levels": {k: float(v) for k, v in key_levels.items()},
            }
        except Exception as e:
            logger.error(f"Error getting Fibonacci signal: {e}")
            return {"signal": "NEUTRAL", "nearest_level": "fib_0.5", "nearest_value": 0.0}

    @staticmethod
    def calculate_all(df: pd.DataFrame) -> pd.DataFrame:
        try:
            df = IchimokuIndicators.calculate_ichimoku(df)
            return df
        except Exception as e:
            logger.error(f"Error calculating all Ichimoku indicators: {e}")
            return df

    @staticmethod
    def get_all_signals(df: pd.DataFrame) -> Dict[str, Any]:
        try:
            ichimoku_signal = IchimokuIndicators.get_ichimoku_signal(df)
            pivots = IchimokuIndicators.pivot_points(df)
            fib_levels = IchimokuIndicators.fibonacci_levels(df)
            pivot_signal = IchimokuIndicators.get_pivot_signal(df, pivots)
            fib_signal = IchimokuIndicators.get_fibonacci_signal(df, fib_levels)

            bullish_count = sum([
                "BULLISH" in ichimoku_signal.get("signal", ""),
                pivot_signal.get("signal") == "BULLISH",
                fib_signal.get("signal") == "BULLISH",
            ])
            bearish_count = sum([
                "BEARISH" in ichimoku_signal.get("signal", ""),
                pivot_signal.get("signal") == "BEARISH",
                fib_signal.get("signal") == "BEARISH",
            ])

            overall = (
                "BULLISH" if bullish_count > bearish_count
                else "BEARISH" if bearish_count > bullish_count
                else "NEUTRAL"
            )

            return {
                "ichimoku": ichimoku_signal,
                "pivots": pivot_signal,
                "fibonacci": fib_signal,
                "pivot_levels": pivots,
                "fib_levels": fib_levels,
                "overall": overall,
                "bullish_count": bullish_count,
                "bearish_count": bearish_count,
            }
        except Exception as e:
            logger.error(f"Error getting all Ichimoku signals: {e}")
            return {"overall": "NEUTRAL"}


__all__ = ["IchimokuIndicators"]

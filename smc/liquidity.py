import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from utils.logger import logger


class LiquidityAnalysis:

    @staticmethod
    def detect_equal_highs(
        df: pd.DataFrame,
        lookback: int = 50,
        tolerance: float = 0.002,
        min_touches: int = 2,
    ) -> List[Dict[str, Any]]:
        try:
            data = df.iloc[-lookback:].copy().reset_index(drop=True)
            highs = data["high"].values
            equal_highs = []

            for i in range(len(highs)):
                level = highs[i]
                touches = []

                for j in range(len(highs)):
                    if abs(highs[j] - level) / level <= tolerance:
                        touches.append(j)

                if len(touches) >= min_touches and i == touches[0]:
                    liquidity = {
                        "type": "EQUAL_HIGH",
                        "level": float(level),
                        "touches": len(touches),
                        "indices": touches,
                        "strength": float(len(touches) * level),
                        "is_swept": False,
                    }

                    future_idx = max(touches) + 1
                    if future_idx < len(data):
                        future_highs = data.iloc[future_idx:]["high"].values
                        swept = any(h > level * (1 + tolerance) for h in future_highs)
                        liquidity["is_swept"] = swept

                    equal_highs.append(liquidity)

            seen_levels = set()
            unique_eqh = []
            for eqh in equal_highs:
                level_key = round(eqh["level"], 4)
                if level_key not in seen_levels:
                    seen_levels.add(level_key)
                    unique_eqh.append(eqh)

            return sorted(unique_eqh, key=lambda x: x["touches"], reverse=True)
        except Exception as e:
            logger.error(f"Error detecting equal highs: {e}")
            return []

    @staticmethod
    def detect_equal_lows(
        df: pd.DataFrame,
        lookback: int = 50,
        tolerance: float = 0.002,
        min_touches: int = 2,
    ) -> List[Dict[str, Any]]:
        try:
            data = df.iloc[-lookback:].copy().reset_index(drop=True)
            lows = data["low"].values
            equal_lows = []

            for i in range(len(lows)):
                level = lows[i]
                touches = []

                for j in range(len(lows)):
                    if abs(lows[j] - level) / level <= tolerance:
                        touches.append(j)

                if len(touches) >= min_touches and i == touches[0]:
                    liquidity = {
                        "type": "EQUAL_LOW",
                        "level": float(level),
                        "touches": len(touches),
                        "indices": touches,
                        "strength": float(len(touches) * level),
                        "is_swept": False,
                    }

                    future_idx = max(touches) + 1
                    if future_idx < len(data):
                        future_lows = data.iloc[future_idx:]["low"].values
                        swept = any(l < level * (1 - tolerance) for l in future_lows)
                        liquidity["is_swept"] = swept

                    equal_lows.append(liquidity)

            seen_levels = set()
            unique_eql = []
            for eql in equal_lows:
                level_key = round(eql["level"], 4)
                if level_key not in seen_levels:
                    seen_levels.add(level_key)
                    unique_eql.append(eql)

            return sorted(unique_eql, key=lambda x: x["touches"], reverse=True)
        except Exception as e:
            logger.error(f"Error detecting equal lows: {e}")
            return []

    @staticmethod
    def detect_liquidity_sweep(
        df: pd.DataFrame,
        lookback: int = 50,
        tolerance: float = 0.002,
    ) -> List[Dict[str, Any]]:
        try:
            data = df.iloc[-lookback:].copy().reset_index(drop=True)
            sweeps = []

            for i in range(10, len(data)):
                current = data.iloc[i]
                prev_data = data.iloc[max(0, i - 20):i]

                recent_high = float(prev_data["high"].max())
                recent_low = float(prev_data["low"].min())

                curr_high = float(current["high"])
                curr_low = float(current["low"])
                curr_close = float(current["close"])
                curr_open = float(current["open"])

                swept_high = curr_high > recent_high and curr_close < recent_high
                swept_low = curr_low < recent_low and curr_close > recent_low

                if swept_high:
                    sweep_amount = (curr_high - recent_high) / recent_high * 100
                    reversal_strength = (curr_high - curr_close) / (curr_high - curr_low) if curr_high != curr_low else 0

                    sweeps.append({
                        "type": "BEARISH_SWEEP",
                        "direction": "BEARISH",
                        "index": i,
                        "swept_level": float(recent_high),
                        "sweep_high": float(curr_high),
                        "close": float(curr_close),
                        "sweep_amount_pct": float(sweep_amount),
                        "reversal_strength": float(reversal_strength),
                        "is_strong": reversal_strength > 0.6,
                    })

                if swept_low:
                    sweep_amount = (recent_low - curr_low) / recent_low * 100
                    reversal_strength = (curr_close - curr_low) / (curr_high - curr_low) if curr_high != curr_low else 0

                    sweeps.append({
                        "type": "BULLISH_SWEEP",
                        "direction": "BULLISH",
                        "index": i,
                        "swept_level": float(recent_low),
                        "sweep_low": float(curr_low),
                        "close": float(curr_close),
                        "sweep_amount_pct": float(sweep_amount),
                        "reversal_strength": float(reversal_strength),
                        "is_strong": reversal_strength > 0.6,
                    })

            return sorted(sweeps, key=lambda x: x["index"], reverse=True)
        except Exception as e:
            logger.error(f"Error detecting liquidity sweep: {e}")
            return []

    @staticmethod
    def detect_liquidity_grab(
        df: pd.DataFrame,
        lookback: int = 30,
    ) -> List[Dict[str, Any]]:
        try:
            data = df.iloc[-lookback:].copy().reset_index(drop=True)
            grabs = []

            for i in range(5, len(data)):
                current = data.iloc[i]
                prev_5 = data.iloc[max(0, i - 5):i]

                curr_high = float(current["high"])
                curr_low = float(current["low"])
                curr_close = float(current["close"])
                curr_open = float(current["open"])
                body = abs(curr_close - curr_open)
                total_range = curr_high - curr_low

                if total_range == 0:
                    continue

                upper_wick = curr_high - max(curr_open, curr_close)
                lower_wick = min(curr_open, curr_close) - curr_low

                upper_wick_ratio = upper_wick / total_range
                lower_wick_ratio = lower_wick / total_range

                prev_high = float(prev_5["high"].max())
                prev_low = float(prev_5["low"].min())

                if (
                    upper_wick_ratio > 0.5
                    and curr_high > prev_high
                    and curr_close < prev_high
                ):
                    grabs.append({
                        "type": "BEARISH_GRAB",
                        "direction": "BEARISH",
                        "index": i,
                        "level": float(prev_high),
                        "wick_high": float(curr_high),
                        "close": float(curr_close),
                        "wick_ratio": float(upper_wick_ratio),
                        "strength": float(upper_wick_ratio * (curr_high - prev_high) / prev_high * 100),
                    })

                if (
                    lower_wick_ratio > 0.5
                    and curr_low < prev_low
                    and curr_close > prev_low
                ):
                    grabs.append({
                        "type": "BULLISH_GRAB",
                        "direction": "BULLISH",
                        "index": i,
                        "level": float(prev_low),
                        "wick_low": float(curr_low),
                        "close": float(curr_close),
                        "wick_ratio": float(lower_wick_ratio),
                        "strength": float(lower_wick_ratio * (prev_low - curr_low) / prev_low * 100),
                    })

            return sorted(grabs, key=lambda x: x["index"], reverse=True)
        except Exception as e:
            logger.error(f"Error detecting liquidity grab: {e}")
            return []

    @staticmethod
    def get_liquidity_levels(
        df: pd.DataFrame,
        lookback: int = 100,
    ) -> Dict[str, Any]:
        try:
            close = float(df.iloc[-1]["close"])

            eq_highs = LiquidityAnalysis.detect_equal_highs(df, lookback)
            eq_lows = LiquidityAnalysis.detect_equal_lows(df, lookback)

            active_eq_highs = [e for e in eq_highs if not e["is_swept"] and e["level"] > close]
            active_eq_lows = [e for e in eq_lows if not e["is_swept"] and e["level"] < close]

            nearest_high_liq = (
                min(active_eq_highs, key=lambda x: abs(x["level"] - close))
                if active_eq_highs else None
            )
            nearest_low_liq = (
                min(active_eq_lows, key=lambda x: abs(x["level"] - close))
                if active_eq_lows else None
            )

            return {
                "equal_highs": eq_highs[:5],
                "equal_lows": eq_lows[:5],
                "active_eq_highs": active_eq_highs[:3],
                "active_eq_lows": active_eq_lows[:3],
                "nearest_high_liquidity": nearest_high_liq,
                "nearest_low_liquidity": nearest_low_liq,
                "total_high_pools": len(active_eq_highs),
                "total_low_pools": len(active_eq_lows),
            }
        except Exception as e:
            logger.error(f"Error getting liquidity levels: {e}")
            return {
                "equal_highs": [],
                "equal_lows": [],
                "active_eq_highs": [],
                "active_eq_lows": [],
                "nearest_high_liquidity": None,
                "nearest_low_liquidity": None,
                "total_high_pools": 0,
                "total_low_pools": 0,
            }

    @staticmethod
    def get_recent_sweep(df: pd.DataFrame, bars: int = 5) -> Optional[Dict[str, Any]]:
        try:
            sweeps = LiquidityAnalysis.detect_liquidity_sweep(df)
            recent_sweeps = [s for s in sweeps if s["index"] >= len(df) - bars - 1]
            if recent_sweeps:
                return max(recent_sweeps, key=lambda x: x["reversal_strength"])
            return None
        except Exception as e:
            logger.error(f"Error getting recent sweep: {e}")
            return None

    @staticmethod
    def get_recent_grab(df: pd.DataFrame, bars: int = 3) -> Optional[Dict[str, Any]]:
        try:
            grabs = LiquidityAnalysis.detect_liquidity_grab(df)
            recent_grabs = [g for g in grabs if g["index"] >= len(df) - bars - 1]
            if recent_grabs:
                return max(recent_grabs, key=lambda x: x["strength"])
            return None
        except Exception as e:
            logger.error(f"Error getting recent grab: {e}")
            return None

    @staticmethod
    def get_signal(df: pd.DataFrame) -> Dict[str, Any]:
        try:
            close = float(df.iloc[-1]["close"])
            liq_levels = LiquidityAnalysis.get_liquidity_levels(df)
            recent_sweep = LiquidityAnalysis.get_recent_sweep(df)
            recent_grab = LiquidityAnalysis.get_recent_grab(df)
            sweeps = LiquidityAnalysis.detect_liquidity_sweep(df)
            grabs = LiquidityAnalysis.detect_liquidity_grab(df)

            recent_sweeps = [s for s in sweeps if s["index"] >= len(df) - 5]
            recent_grabs = [g for g in grabs if g["index"] >= len(df) - 3]

            bullish_sweep = any(s["direction"] == "BULLISH" for s in recent_sweeps)
            bearish_sweep = any(s["direction"] == "BEARISH" for s in recent_sweeps)
            bullish_grab = any(g["direction"] == "BULLISH" for g in recent_grabs)
            bearish_grab = any(g["direction"] == "BEARISH" for g in recent_grabs)

            nearest_high = liq_levels.get("nearest_high_liquidity")
            nearest_low = liq_levels.get("nearest_low_liquidity")

            price_near_high_liq = (
                nearest_high is not None
                and abs(close - nearest_high["level"]) / close < 0.005
            )
            price_near_low_liq = (
                nearest_low is not None
                and abs(close - nearest_low["level"]) / close < 0.005
            )

            if bullish_sweep or bullish_grab:
                signal = "BULLISH"
            elif bearish_sweep or bearish_grab:
                signal = "BEARISH"
            elif price_near_low_liq:
                signal = "BULLISH"
            elif price_near_high_liq:
                signal = "BEARISH"
            else:
                signal = "NEUTRAL"

            sweep_confirmation = bullish_sweep or bearish_sweep
            grab_confirmation = bullish_grab or bearish_grab

            return {
                "signal": signal,
                "bullish_sweep": bullish_sweep,
                "bearish_sweep": bearish_sweep,
                "bullish_grab": bullish_grab,
                "bearish_grab": bearish_grab,
                "recent_sweep": recent_sweep,
                "recent_grab": recent_grab,
                "price_near_high_liquidity": price_near_high_liq,
                "price_near_low_liquidity": price_near_low_liq,
                "nearest_high_liquidity": nearest_high,
                "nearest_low_liquidity": nearest_low,
                "total_high_pools": liq_levels.get("total_high_pools", 0),
                "total_low_pools": liq_levels.get("total_low_pools", 0),
                "sweep_confirmation": sweep_confirmation,
                "grab_confirmation": grab_confirmation,
                "confirmation": sweep_confirmation or grab_confirmation,
            }
        except Exception as e:
            logger.error(f"Error getting liquidity signal: {e}")
            return {"signal": "NEUTRAL", "confirmation": False}


__all__ = ["LiquidityAnalysis"]

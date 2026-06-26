import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from utils.logger import logger


class FairValueGap:

    @staticmethod
    def detect_bullish_fvg(
        df: pd.DataFrame,
        lookback: int = 50,
        min_gap_pct: float = 0.001,
    ) -> List[Dict[str, Any]]:
        try:
            fvgs = []
            data = df.iloc[-lookback:].copy().reset_index(drop=True)

            for i in range(1, len(data) - 1):
                candle_1 = data.iloc[i - 1]
                candle_2 = data.iloc[i]
                candle_3 = data.iloc[i + 1]

                gap_bottom = float(candle_1["high"])
                gap_top = float(candle_3["low"])

                if gap_top <= gap_bottom:
                    continue

                gap_size = gap_top - gap_bottom
                gap_pct = gap_size / gap_bottom

                if gap_pct < min_gap_pct:
                    continue

                is_bullish_impulse = (
                    float(candle_2["close"]) > float(candle_2["open"])
                )

                future_data = data.iloc[i + 1:]
                is_filled = any(future_data["low"] <= gap_bottom)
                partially_filled = any(
                    (future_data["low"] <= gap_top) &
                    (future_data["low"] > gap_bottom)
                )
                times_tested = int(sum(
                    (future_data["low"] <= gap_top) &
                    (future_data["low"] >= gap_bottom)
                ))

                fvg = {
                    "type": "BULLISH",
                    "index": i,
                    "top": float(gap_top),
                    "bottom": float(gap_bottom),
                    "mid": float((gap_top + gap_bottom) / 2),
                    "size": float(gap_size),
                    "size_pct": float(gap_pct * 100),
                    "is_filled": is_filled,
                    "partially_filled": partially_filled,
                    "times_tested": times_tested,
                    "is_bullish_impulse": is_bullish_impulse,
                    "strength": float(gap_pct * 100 * (1 + times_tested * 0.1)),
                }
                fvgs.append(fvg)

            active_fvgs = [f for f in fvgs if not f["is_filled"]]
            active_fvgs.sort(key=lambda x: x["strength"], reverse=True)
            return active_fvgs
        except Exception as e:
            logger.error(f"Error detecting bullish FVG: {e}")
            return []

    @staticmethod
    def detect_bearish_fvg(
        df: pd.DataFrame,
        lookback: int = 50,
        min_gap_pct: float = 0.001,
    ) -> List[Dict[str, Any]]:
        try:
            fvgs = []
            data = df.iloc[-lookback:].copy().reset_index(drop=True)

            for i in range(1, len(data) - 1):
                candle_1 = data.iloc[i - 1]
                candle_2 = data.iloc[i]
                candle_3 = data.iloc[i + 1]

                gap_top = float(candle_1["low"])
                gap_bottom = float(candle_3["high"])

                if gap_bottom >= gap_top:
                    continue

                gap_size = gap_top - gap_bottom
                gap_pct = gap_size / gap_top

                if gap_pct < min_gap_pct:
                    continue

                is_bearish_impulse = (
                    float(candle_2["close"]) < float(candle_2["open"])
                )

                future_data = data.iloc[i + 1:]
                is_filled = any(future_data["high"] >= gap_top)
                partially_filled = any(
                    (future_data["high"] >= gap_bottom) &
                    (future_data["high"] < gap_top)
                )
                times_tested = int(sum(
                    (future_data["high"] >= gap_bottom) &
                    (future_data["high"] <= gap_top)
                ))

                fvg = {
                    "type": "BEARISH",
                    "index": i,
                    "top": float(gap_top),
                    "bottom": float(gap_bottom),
                    "mid": float((gap_top + gap_bottom) / 2),
                    "size": float(gap_size),
                    "size_pct": float(gap_pct * 100),
                    "is_filled": is_filled,
                    "partially_filled": partially_filled,
                    "times_tested": times_tested,
                    "is_bearish_impulse": is_bearish_impulse,
                    "strength": float(gap_pct * 100 * (1 + times_tested * 0.1)),
                }
                fvgs.append(fvg)

            active_fvgs = [f for f in fvgs if not f["is_filled"]]
            active_fvgs.sort(key=lambda x: x["strength"], reverse=True)
            return active_fvgs
        except Exception as e:
            logger.error(f"Error detecting bearish FVG: {e}")
            return []

    @staticmethod
    def get_nearest_fvg(
        df: pd.DataFrame,
        direction: str,
        lookback: int = 50,
    ) -> Optional[Dict[str, Any]]:
        try:
            close = float(df.iloc[-1]["close"])

            if direction == "LONG":
                fvgs = FairValueGap.detect_bullish_fvg(df, lookback)
                valid_fvgs = [
                    f for f in fvgs
                    if f["bottom"] <= close <= f["top"] * 1.005
                ]
            else:
                fvgs = FairValueGap.detect_bearish_fvg(df, lookback)
                valid_fvgs = [
                    f for f in fvgs
                    if f["bottom"] * 0.995 <= close <= f["top"]
                ]

            if not valid_fvgs:
                return None

            nearest = min(valid_fvgs, key=lambda x: abs(close - x["mid"]))
            return nearest
        except Exception as e:
            logger.error(f"Error getting nearest FVG: {e}")
            return None

    @staticmethod
    def is_price_in_fvg(
        df: pd.DataFrame,
        direction: str,
        tolerance: float = 0.002,
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        try:
            close = float(df.iloc[-1]["close"])

            if direction == "LONG":
                fvgs = FairValueGap.detect_bullish_fvg(df)
            else:
                fvgs = FairValueGap.detect_bearish_fvg(df)

            for fvg in fvgs:
                fvg_range = fvg["top"] - fvg["bottom"]
                tol = fvg_range * tolerance if fvg_range > 0 else fvg["top"] * tolerance

                if fvg["bottom"] - tol <= close <= fvg["top"] + tol:
                    return True, fvg

            return False, None
        except Exception as e:
            logger.error(f"Error checking price in FVG: {e}")
            return False, None

    @staticmethod
    def get_fvg_zones(
        df: pd.DataFrame,
        lookback: int = 100,
    ) -> Dict[str, List[Dict[str, Any]]]:
        try:
            close = float(df.iloc[-1]["close"])

            bull_fvgs = FairValueGap.detect_bullish_fvg(df, lookback)
            bear_fvgs = FairValueGap.detect_bearish_fvg(df, lookback)

            bull_below = [f for f in bull_fvgs if f["top"] < close]
            bear_above = [f for f in bear_fvgs if f["bottom"] > close]

            in_bull_fvg = [f for f in bull_fvgs if f["bottom"] <= close <= f["top"]]
            in_bear_fvg = [f for f in bear_fvgs if f["bottom"] <= close <= f["top"]]

            return {
                "bullish_fvgs": bull_fvgs,
                "bearish_fvgs": bear_fvgs,
                "support_fvgs": sorted(bull_below, key=lambda x: x["top"], reverse=True)[:3],
                "resistance_fvgs": sorted(bear_above, key=lambda x: x["bottom"])[:3],
                "current_bull_fvg": in_bull_fvg[0] if in_bull_fvg else None,
                "current_bear_fvg": in_bear_fvg[0] if in_bear_fvg else None,
            }
        except Exception as e:
            logger.error(f"Error getting FVG zones: {e}")
            return {
                "bullish_fvgs": [],
                "bearish_fvgs": [],
                "support_fvgs": [],
                "resistance_fvgs": [],
                "current_bull_fvg": None,
                "current_bear_fvg": None,
            }

    @staticmethod
    def detect_fvg_stack(
        df: pd.DataFrame,
        direction: str,
        lookback: int = 50,
        min_stack: int = 2,
    ) -> bool:
        try:
            if direction == "LONG":
                fvgs = FairValueGap.detect_bullish_fvg(df, lookback)
            else:
                fvgs = FairValueGap.detect_bearish_fvg(df, lookback)

            close = float(df.iloc[-1]["close"])
            nearby_fvgs = [
                f for f in fvgs
                if abs(f["mid"] - close) / close < 0.02
            ]
            return len(nearby_fvgs) >= min_stack
        except Exception as e:
            logger.error(f"Error detecting FVG stack: {e}")
            return False

    @staticmethod
    def get_signal(df: pd.DataFrame) -> Dict[str, Any]:
        try:
            close = float(df.iloc[-1]["close"])
            zones = FairValueGap.get_fvg_zones(df)

            in_bull_fvg = zones.get("current_bull_fvg") is not None
            in_bear_fvg = zones.get("current_bear_fvg") is not None

            bull_stack = FairValueGap.detect_fvg_stack(df, "LONG")
            bear_stack = FairValueGap.detect_fvg_stack(df, "SHORT")

            support_fvgs = zones.get("support_fvgs", [])
            resistance_fvgs = zones.get("resistance_fvgs", [])

            nearest_support = support_fvgs[0] if support_fvgs else None
            nearest_resistance = resistance_fvgs[0] if resistance_fvgs else None

            if in_bull_fvg:
                signal = "BULLISH"
            elif in_bear_fvg:
                signal = "BEARISH"
            elif nearest_support and abs(close - nearest_support["top"]) / close < 0.005:
                signal = "BULLISH"
            elif nearest_resistance and abs(close - nearest_resistance["bottom"]) / close < 0.005:
                signal = "BEARISH"
            else:
                signal = "NEUTRAL"

            return {
                "signal": signal,
                "in_bullish_fvg": in_bull_fvg,
                "in_bearish_fvg": in_bear_fvg,
                "bullish_fvg_stack": bull_stack,
                "bearish_fvg_stack": bear_stack,
                "current_bull_fvg": zones.get("current_bull_fvg"),
                "current_bear_fvg": zones.get("current_bear_fvg"),
                "nearest_support_fvg": nearest_support,
                "nearest_resistance_fvg": nearest_resistance,
                "total_bull_fvgs": len(zones.get("bullish_fvgs", [])),
                "total_bear_fvgs": len(zones.get("bearish_fvgs", [])),
                "confirmation": in_bull_fvg or in_bear_fvg,
            }
        except Exception as e:
            logger.error(f"Error getting FVG signal: {e}")
            return {"signal": "NEUTRAL", "confirmation": False}


__all__ = ["FairValueGap"]

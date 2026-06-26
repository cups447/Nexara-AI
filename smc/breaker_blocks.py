import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from utils.logger import logger


class BreakerBlocks:

    @staticmethod
    def detect_bullish_breaker(
        df: pd.DataFrame,
        lookback: int = 100,
        swing_lookback: int = 5,
    ) -> List[Dict[str, Any]]:
        try:
            data = df.iloc[-lookback:].copy().reset_index(drop=True)
            breakers = []

            for i in range(swing_lookback, len(data) - swing_lookback):
                candle = data.iloc[i]
                high_c = float(candle["high"])
                low_c = float(candle["low"])
                open_c = float(candle["open"])
                close_c = float(candle["close"])

                is_bearish_ob = close_c < open_c

                if not is_bearish_ob:
                    continue

                left_highs = [float(data.iloc[i - j]["high"]) for j in range(1, swing_lookback + 1)]
                is_swing_high = all(high_c >= h for h in left_highs)

                if not is_swing_high:
                    continue

                future_data = data.iloc[i + 1:]
                swept = False
                sweep_idx = None

                for j, (_, fut_candle) in enumerate(future_data.iterrows()):
                    if float(fut_candle["low"]) < low_c:
                        swept = True
                        sweep_idx = i + j + 1
                        break

                if not swept:
                    continue

                if sweep_idx is None or sweep_idx >= len(data):
                    continue

                after_sweep = data.iloc[sweep_idx + 1:]
                broken_high = False
                break_idx = None
                break_close = None

                for j, (_, after_candle) in enumerate(after_sweep.iterrows()):
                    if float(after_candle["close"]) > high_c:
                        broken_high = True
                        break_idx = sweep_idx + j + 1
                        break_close = float(after_candle["close"])
                        break

                if not broken_high:
                    continue

                future_after_break = data.iloc[break_idx + 1:] if break_idx else pd.DataFrame()
                is_mitigated = False
                if not future_after_break.empty:
                    is_mitigated = any(
                        float(c["close"]) < low_c
                        for _, c in future_after_break.iterrows()
                    )

                times_tested = 0
                if not future_after_break.empty:
                    for _, test_candle in future_after_break.iterrows():
                        if low_c <= float(test_candle["low"]) <= high_c:
                            times_tested += 1

                breaker_strength = (
                    (break_close - high_c) / high_c * 100
                    if break_close else 0.0
                )

                breakers.append({
                    "type": "BULLISH_BREAKER",
                    "direction": "BULLISH",
                    "top": float(high_c),
                    "bottom": float(low_c),
                    "mid": float((high_c + low_c) / 2),
                    "open": float(open_c),
                    "close": float(close_c),
                    "ob_index": i,
                    "sweep_index": sweep_idx,
                    "break_index": break_idx,
                    "break_close": float(break_close) if break_close else 0.0,
                    "is_mitigated": is_mitigated,
                    "times_tested": times_tested,
                    "strength": float(breaker_strength),
                })

            return sorted(breakers, key=lambda x: x["strength"], reverse=True)
        except Exception as e:
            logger.error(f"Error detecting bullish breaker blocks: {e}")
            return []

    @staticmethod
    def detect_bearish_breaker(
        df: pd.DataFrame,
        lookback: int = 100,
        swing_lookback: int = 5,
    ) -> List[Dict[str, Any]]:
        try:
            data = df.iloc[-lookback:].copy().reset_index(drop=True)
            breakers = []

            for i in range(swing_lookback, len(data) - swing_lookback):
                candle = data.iloc[i]
                high_c = float(candle["high"])
                low_c = float(candle["low"])
                open_c = float(candle["open"])
                close_c = float(candle["close"])

                is_bullish_ob = close_c > open_c

                if not is_bullish_ob:
                    continue

                left_lows = [float(data.iloc[i - j]["low"]) for j in range(1, swing_lookback + 1)]
                is_swing_low = all(low_c <= l for l in left_lows)

                if not is_swing_low:
                    continue

                future_data = data.iloc[i + 1:]
                swept = False
                sweep_idx = None

                for j, (_, fut_candle) in enumerate(future_data.iterrows()):
                    if float(fut_candle["high"]) > high_c:
                        swept = True
                        sweep_idx = i + j + 1
                        break

                if not swept:
                    continue

                if sweep_idx is None or sweep_idx >= len(data):
                    continue

                after_sweep = data.iloc[sweep_idx + 1:]
                broken_low = False
                break_idx = None
                break_close = None

                for j, (_, after_candle) in enumerate(after_sweep.iterrows()):
                    if float(after_candle["close"]) < low_c:
                        broken_low = True
                        break_idx = sweep_idx + j + 1
                        break_close = float(after_candle["close"])
                        break

                if not broken_low:
                    continue

                future_after_break = data.iloc[break_idx + 1:] if break_idx else pd.DataFrame()
                is_mitigated = False
                if not future_after_break.empty:
                    is_mitigated = any(
                        float(c["close"]) > high_c
                        for _, c in future_after_break.iterrows()
                    )

                times_tested = 0
                if not future_after_break.empty:
                    for _, test_candle in future_after_break.iterrows():
                        if low_c <= float(test_candle["high"]) <= high_c:
                            times_tested += 1

                breaker_strength = (
                    (low_c - break_close) / low_c * 100
                    if break_close else 0.0
                )

                breakers.append({
                    "type": "BEARISH_BREAKER",
                    "direction": "BEARISH",
                    "top": float(high_c),
                    "bottom": float(low_c),
                    "mid": float((high_c + low_c) / 2),
                    "open": float(open_c),
                    "close": float(close_c),
                    "ob_index": i,
                    "sweep_index": sweep_idx,
                    "break_index": break_idx,
                    "break_close": float(break_close) if break_close else 0.0,
                    "is_mitigated": is_mitigated,
                    "times_tested": times_tested,
                    "strength": float(breaker_strength),
                })

            return sorted(breakers, key=lambda x: x["strength"], reverse=True)
        except Exception as e:
            logger.error(f"Error detecting bearish breaker blocks: {e}")
            return []

    @staticmethod
    def detect_mitigation_blocks(
        df: pd.DataFrame,
        lookback: int = 100,
    ) -> List[Dict[str, Any]]:
        try:
            data = df.iloc[-lookback:].copy().reset_index(drop=True)
            mitigation_blocks = []

            for i in range(5, len(data) - 1):
                candle = data.iloc[i]
                high_c = float(candle["high"])
                low_c = float(candle["low"])
                open_c = float(candle["open"])
                close_c = float(candle["close"])

                body_size = abs(close_c - open_c)
                total_range = high_c - low_c

                if total_range == 0:
                    continue

                body_pct = body_size / total_range

                if body_pct < 0.5:
                    continue

                prev_data = data.iloc[max(0, i - 10):i]
                is_bullish = close_c > open_c

                if is_bullish:
                    prev_high = float(prev_data["high"].max())
                    is_mitigation = high_c >= prev_high * 0.998

                    if not is_mitigation:
                        continue

                    future_data = data.iloc[i + 1:]
                    retraced = any(float(c["low"]) <= low_c for _, c in future_data.iterrows())

                    if retraced:
                        mitigation_blocks.append({
                            "type": "BULLISH_MITIGATION",
                            "direction": "BULLISH",
                            "top": float(high_c),
                            "bottom": float(low_c),
                            "mid": float((high_c + low_c) / 2),
                            "index": i,
                            "body_pct": float(body_pct),
                            "mitigated_level": float(prev_high),
                        })
                else:
                    prev_low = float(prev_data["low"].min())
                    is_mitigation = low_c <= prev_low * 1.002

                    if not is_mitigation:
                        continue

                    future_data = data.iloc[i + 1:]
                    retraced = any(float(c["high"]) >= high_c for _, c in future_data.iterrows())

                    if retraced:
                        mitigation_blocks.append({
                            "type": "BEARISH_MITIGATION",
                            "direction": "BEARISH",
                            "top": float(high_c),
                            "bottom": float(low_c),
                            "mid": float((high_c + low_c) / 2),
                            "index": i,
                            "body_pct": float(body_pct),
                            "mitigated_level": float(prev_low),
                        })

            return sorted(mitigation_blocks, key=lambda x: x["index"], reverse=True)
        except Exception as e:
            logger.error(f"Error detecting mitigation blocks: {e}")
            return []

    @staticmethod
    def is_price_at_breaker(
        df: pd.DataFrame,
        direction: str,
        tolerance: float = 0.003,
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        try:
            close = float(df.iloc[-1]["close"])

            if direction == "LONG":
                breakers = BreakerBlocks.detect_bullish_breaker(df)
            else:
                breakers = BreakerBlocks.detect_bearish_breaker(df)

            active_breakers = [b for b in breakers if not b["is_mitigated"]]

            for breaker in active_breakers:
                top = breaker["top"]
                bottom = breaker["bottom"]
                tol = (top - bottom) * tolerance

                if bottom - tol <= close <= top + tol:
                    return True, breaker

            return False, None
        except Exception as e:
            logger.error(f"Error checking price at breaker: {e}")
            return False, None

    @staticmethod
    def get_active_breakers(
        df: pd.DataFrame,
        lookback: int = 100,
    ) -> Dict[str, List[Dict[str, Any]]]:
        try:
            close = float(df.iloc[-1]["close"])

            bull_breakers = [
                b for b in BreakerBlocks.detect_bullish_breaker(df, lookback)
                if not b["is_mitigated"]
            ]
            bear_breakers = [
                b for b in BreakerBlocks.detect_bearish_breaker(df, lookback)
                if not b["is_mitigated"]
            ]
            mitigation = BreakerBlocks.detect_mitigation_blocks(df, lookback)

            support_breakers = sorted(
                [b for b in bull_breakers if b["top"] < close],
                key=lambda x: x["top"],
                reverse=True,
            )[:3]

            resistance_breakers = sorted(
                [b for b in bear_breakers if b["bottom"] > close],
                key=lambda x: x["bottom"],
            )[:3]

            return {
                "bullish_breakers": bull_breakers,
                "bearish_breakers": bear_breakers,
                "mitigation_blocks": mitigation[:5],
                "support_breakers": support_breakers,
                "resistance_breakers": resistance_breakers,
            }
        except Exception as e:
            logger.error(f"Error getting active breakers: {e}")
            return {
                "bullish_breakers": [],
                "bearish_breakers": [],
                "mitigation_blocks": [],
                "support_breakers": [],
                "resistance_breakers": [],
            }

    @staticmethod
    def get_signal(df: pd.DataFrame) -> Dict[str, Any]:
        try:
            close = float(df.iloc[-1]["close"])
            active = BreakerBlocks.get_active_breakers(df)

            at_bull_breaker, bull_breaker = BreakerBlocks.is_price_at_breaker(df, "LONG")
            at_bear_breaker, bear_breaker = BreakerBlocks.is_price_at_breaker(df, "SHORT")

            support_breakers = active.get("support_breakers", [])
            resistance_breakers = active.get("resistance_breakers", [])
            mitigation_blocks = active.get("mitigation_blocks", [])

            nearest_support = support_breakers[0] if support_breakers else None
            nearest_resistance = resistance_breakers[0] if resistance_breakers else None

            recent_mitigation = [
                m for m in mitigation_blocks
                if m["index"] >= len(df) - 10
            ]
            bullish_mitigation = any(m["direction"] == "BULLISH" for m in recent_mitigation)
            bearish_mitigation = any(m["direction"] == "BEARISH" for m in recent_mitigation)

            if at_bull_breaker:
                signal = "BULLISH"
            elif at_bear_breaker:
                signal = "BEARISH"
            elif bullish_mitigation:
                signal = "BULLISH"
            elif bearish_mitigation:
                signal = "BEARISH"
            else:
                signal = "NEUTRAL"

            confirmation = at_bull_breaker or at_bear_breaker

            return {
                "signal": signal,
                "at_bullish_breaker": at_bull_breaker,
                "at_bearish_breaker": at_bear_breaker,
                "bullish_breaker": bull_breaker,
                "bearish_breaker": bear_breaker,
                "nearest_support_breaker": nearest_support,
                "nearest_resistance_breaker": nearest_resistance,
                "bullish_mitigation": bullish_mitigation,
                "bearish_mitigation": bearish_mitigation,
                "total_bull_breakers": len(active.get("bullish_breakers", [])),
                "total_bear_breakers": len(active.get("bearish_breakers", [])),
                "confirmation": confirmation,
            }
        except Exception as e:
            logger.error(f"Error getting breaker block signal: {e}")
            return {"signal": "NEUTRAL", "confirmation": False}


__all__ = ["BreakerBlocks"]

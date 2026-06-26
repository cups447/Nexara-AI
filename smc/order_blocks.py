import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from utils.logger import logger


class OrderBlocks:

    @staticmethod
    def detect_bullish_order_blocks(
        df: pd.DataFrame,
        lookback: int = 50,
        min_body_pct: float = 0.4,
    ) -> List[Dict[str, Any]]:
        try:
            order_blocks = []
            data = df.iloc[-lookback:].copy().reset_index(drop=True)

            for i in range(1, len(data) - 1):
                candle = data.iloc[i]
                next_candle = data.iloc[i + 1]

                open_c = float(candle["open"])
                close_c = float(candle["close"])
                high_c = float(candle["high"])
                low_c = float(candle["low"])

                body = abs(close_c - open_c)
                total_range = high_c - low_c
                if total_range == 0:
                    continue
                body_pct = body / total_range

                is_bearish = close_c < open_c
                if not is_bearish or body_pct < min_body_pct:
                    continue

                next_close = float(next_candle["close"])
                next_open = float(next_candle["open"])
                strong_bullish_next = next_close > next_open and next_close > high_c

                if not strong_bullish_next:
                    continue

                future_data = data.iloc[i + 1:]
                price_returned = future_data["low"].min() <= high_c
                price_tested = any(
                    (future_data["low"] <= high_c) &
                    (future_data["close"] >= low_c)
                )
                is_mitigated = any(future_data["close"] < low_c)

                ob = {
                    "type": "BULLISH",
                    "index": i,
                    "top": float(high_c),
                    "bottom": float(low_c),
                    "open": float(open_c),
                    "close": float(close_c),
                    "mid": float((high_c + low_c) / 2),
                    "body_pct": float(body_pct),
                    "strength": float(body_pct * (next_close - high_c) / high_c * 100),
                    "is_mitigated": is_mitigated,
                    "price_tested": price_tested,
                    "timestamp": df.index[-(lookback - i)] if hasattr(df.index, '__len__') else i,
                }
                order_blocks.append(ob)

            order_blocks.sort(key=lambda x: x["strength"], reverse=True)
            return order_blocks
        except Exception as e:
            logger.error(f"Error detecting bullish order blocks: {e}")
            return []

    @staticmethod
    def detect_bearish_order_blocks(
        df: pd.DataFrame,
        lookback: int = 50,
        min_body_pct: float = 0.4,
    ) -> List[Dict[str, Any]]:
        try:
            order_blocks = []
            data = df.iloc[-lookback:].copy().reset_index(drop=True)

            for i in range(1, len(data) - 1):
                candle = data.iloc[i]
                next_candle = data.iloc[i + 1]

                open_c = float(candle["open"])
                close_c = float(candle["close"])
                high_c = float(candle["high"])
                low_c = float(candle["low"])

                body = abs(close_c - open_c)
                total_range = high_c - low_c
                if total_range == 0:
                    continue
                body_pct = body / total_range

                is_bullish = close_c > open_c
                if not is_bullish or body_pct < min_body_pct:
                    continue

                next_close = float(next_candle["close"])
                next_open = float(next_candle["open"])
                strong_bearish_next = next_close < next_open and next_close < low_c

                if not strong_bearish_next:
                    continue

                future_data = data.iloc[i + 1:]
                price_returned = future_data["high"].max() >= low_c
                price_tested = any(
                    (future_data["high"] >= low_c) &
                    (future_data["close"] <= high_c)
                )
                is_mitigated = any(future_data["close"] > high_c)

                ob = {
                    "type": "BEARISH",
                    "index": i,
                    "top": float(high_c),
                    "bottom": float(low_c),
                    "open": float(open_c),
                    "close": float(close_c),
                    "mid": float((high_c + low_c) / 2),
                    "body_pct": float(body_pct),
                    "strength": float(body_pct * (low_c - next_close) / low_c * 100),
                    "is_mitigated": is_mitigated,
                    "price_tested": price_tested,
                    "timestamp": df.index[-(lookback - i)] if hasattr(df.index, '__len__') else i,
                }
                order_blocks.append(ob)

            order_blocks.sort(key=lambda x: x["strength"], reverse=True)
            return order_blocks
        except Exception as e:
            logger.error(f"Error detecting bearish order blocks: {e}")
            return []

    @staticmethod
    def get_nearest_order_block(
        df: pd.DataFrame,
        direction: str,
        lookback: int = 50,
    ) -> Optional[Dict[str, Any]]:
        try:
            close = float(df.iloc[-1]["close"])

            if direction == "LONG":
                obs = OrderBlocks.detect_bullish_order_blocks(df, lookback)
                valid_obs = [
                    ob for ob in obs
                    if ob["bottom"] <= close <= ob["top"] * 1.02
                    and not ob["is_mitigated"]
                ]
            else:
                obs = OrderBlocks.detect_bearish_order_blocks(df, lookback)
                valid_obs = [
                    ob for ob in obs
                    if ob["bottom"] * 0.98 <= close <= ob["top"]
                    and not ob["is_mitigated"]
                ]

            if not valid_obs:
                return None

            nearest = min(
                valid_obs,
                key=lambda x: abs(close - x["mid"])
            )
            return nearest
        except Exception as e:
            logger.error(f"Error getting nearest order block: {e}")
            return None

    @staticmethod
    def is_price_at_order_block(
        df: pd.DataFrame,
        direction: str,
        tolerance: float = 0.003,
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        try:
            close = float(df.iloc[-1]["close"])
            ob = OrderBlocks.get_nearest_order_block(df, direction)

            if ob is None:
                return False, None

            ob_top = ob["top"]
            ob_bottom = ob["bottom"]
            ob_range = ob_top - ob_bottom

            tolerance_range = ob_range * tolerance if ob_range > 0 else ob_top * tolerance

            at_ob = (
                ob_bottom - tolerance_range <= close <= ob_top + tolerance_range
            )
            return at_ob, ob if at_ob else None
        except Exception as e:
            logger.error(f"Error checking price at order block: {e}")
            return False, None

    @staticmethod
    def get_all_active_order_blocks(
        df: pd.DataFrame,
        lookback: int = 100,
    ) -> Dict[str, List[Dict[str, Any]]]:
        try:
            bullish_obs = [
                ob for ob in OrderBlocks.detect_bullish_order_blocks(df, lookback)
                if not ob["is_mitigated"]
            ]
            bearish_obs = [
                ob for ob in OrderBlocks.detect_bearish_order_blocks(df, lookback)
                if not ob["is_mitigated"]
            ]

            close = float(df.iloc[-1]["close"])

            bullish_below = [ob for ob in bullish_obs if ob["top"] < close]
            bearish_above = [ob for ob in bearish_obs if ob["bottom"] > close]

            return {
                "bullish": bullish_obs,
                "bearish": bearish_obs,
                "support_obs": sorted(bullish_below, key=lambda x: x["top"], reverse=True)[:3],
                "resistance_obs": sorted(bearish_above, key=lambda x: x["bottom"])[:3],
            }
        except Exception as e:
            logger.error(f"Error getting all active order blocks: {e}")
            return {"bullish": [], "bearish": [], "support_obs": [], "resistance_obs": []}

    @staticmethod
    def get_signal(df: pd.DataFrame) -> Dict[str, Any]:
        try:
            close = float(df.iloc[-1]["close"])
            all_obs = OrderBlocks.get_all_active_order_blocks(df)

            at_bullish_ob, bullish_ob = OrderBlocks.is_price_at_order_block(df, "LONG")
            at_bearish_ob, bearish_ob = OrderBlocks.is_price_at_order_block(df, "SHORT")

            support_obs = all_obs.get("support_obs", [])
            resistance_obs = all_obs.get("resistance_obs", [])

            nearest_support = support_obs[0] if support_obs else None
            nearest_resistance = resistance_obs[0] if resistance_obs else None

            bullish_confirmation = at_bullish_ob and bullish_ob is not None
            bearish_confirmation = at_bearish_ob and bearish_ob is not None

            signal = "NEUTRAL"
            if bullish_confirmation:
                signal = "BULLISH"
            elif bearish_confirmation:
                signal = "BEARISH"

            return {
                "signal": signal,
                "at_bullish_ob": at_bullish_ob,
                "at_bearish_ob": at_bearish_ob,
                "bullish_ob": bullish_ob,
                "bearish_ob": bearish_ob,
                "nearest_support_ob": nearest_support,
                "nearest_resistance_ob": nearest_resistance,
                "total_bullish_obs": len(all_obs.get("bullish", [])),
                "total_bearish_obs": len(all_obs.get("bearish", [])),
                "confirmation": bullish_confirmation or bearish_confirmation,
            }
        except Exception as e:
            logger.error(f"Error getting order block signal: {e}")
            return {"signal": "NEUTRAL", "confirmation": False}


__all__ = ["OrderBlocks"]

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from utils.logger import logger


class BOSCHOCHDetector:

    @staticmethod
    def find_swing_highs(
        df: pd.DataFrame,
        lookback: int = 5,
    ) -> List[Dict[str, Any]]:
        try:
            data = df.copy().reset_index(drop=True)
            swing_highs = []

            for i in range(lookback, len(data) - lookback):
                current_high = float(data.iloc[i]["high"])
                left_highs = [float(data.iloc[i - j]["high"]) for j in range(1, lookback + 1)]
                right_highs = [float(data.iloc[i + j]["high"]) for j in range(1, lookback + 1)]

                if all(current_high >= h for h in left_highs) and all(current_high >= h for h in right_highs):
                    swing_highs.append({
                        "index": i,
                        "price": current_high,
                        "bar": i,
                    })

            return swing_highs
        except Exception as e:
            logger.error(f"Error finding swing highs: {e}")
            return []

    @staticmethod
    def find_swing_lows(
        df: pd.DataFrame,
        lookback: int = 5,
    ) -> List[Dict[str, Any]]:
        try:
            data = df.copy().reset_index(drop=True)
            swing_lows = []

            for i in range(lookback, len(data) - lookback):
                current_low = float(data.iloc[i]["low"])
                left_lows = [float(data.iloc[i - j]["low"]) for j in range(1, lookback + 1)]
                right_lows = [float(data.iloc[i + j]["low"]) for j in range(1, lookback + 1)]

                if all(current_low <= l for l in left_lows) and all(current_low <= l for l in right_lows):
                    swing_lows.append({
                        "index": i,
                        "price": current_low,
                        "bar": i,
                    })

            return swing_lows
        except Exception as e:
            logger.error(f"Error finding swing lows: {e}")
            return []

    @staticmethod
    def detect_bos(
        df: pd.DataFrame,
        lookback: int = 50,
        swing_lookback: int = 5,
    ) -> List[Dict[str, Any]]:
        try:
            data = df.iloc[-lookback:].copy().reset_index(drop=True)
            bos_events = []

            swing_highs = BOSCHOCHDetector.find_swing_highs(data, swing_lookback)
            swing_lows = BOSCHOCHDetector.find_swing_lows(data, swing_lookback)

            for sh in swing_highs:
                sh_idx = sh["index"]
                sh_price = sh["price"]

                future_candles = data.iloc[sh_idx + 1:]
                for j, (_, candle) in enumerate(future_candles.iterrows()):
                    if float(candle["close"]) > sh_price:
                        bos_events.append({
                            "type": "BULLISH_BOS",
                            "direction": "BULLISH",
                            "broken_level": float(sh_price),
                            "break_index": sh_idx + j + 1,
                            "swing_index": sh_idx,
                            "break_close": float(candle["close"]),
                            "break_strength": float(
                                (float(candle["close"]) - sh_price) / sh_price * 100
                            ),
                            "confirmed": True,
                        })
                        break

            for sl in swing_lows:
                sl_idx = sl["index"]
                sl_price = sl["price"]

                future_candles = data.iloc[sl_idx + 1:]
                for j, (_, candle) in enumerate(future_candles.iterrows()):
                    if float(candle["close"]) < sl_price:
                        bos_events.append({
                            "type": "BEARISH_BOS",
                            "direction": "BEARISH",
                            "broken_level": float(sl_price),
                            "break_index": sl_idx + j + 1,
                            "swing_index": sl_idx,
                            "break_close": float(candle["close"]),
                            "break_strength": float(
                                (sl_price - float(candle["close"])) / sl_price * 100
                            ),
                            "confirmed": True,
                        })
                        break

            return sorted(bos_events, key=lambda x: x["break_index"], reverse=True)
        except Exception as e:
            logger.error(f"Error detecting BOS: {e}")
            return []

    @staticmethod
    def detect_choch(
        df: pd.DataFrame,
        lookback: int = 50,
        swing_lookback: int = 5,
    ) -> List[Dict[str, Any]]:
        try:
            data = df.iloc[-lookback:].copy().reset_index(drop=True)
            choch_events = []

            swing_highs = BOSCHOCHDetector.find_swing_highs(data, swing_lookback)
            swing_lows = BOSCHOCHDetector.find_swing_lows(data, swing_lookback)

            if len(swing_highs) < 2 or len(swing_lows) < 2:
                return []

            for i in range(1, len(swing_highs)):
                prev_sh = swing_highs[i - 1]
                curr_sh = swing_highs[i]

                if curr_sh["price"] < prev_sh["price"]:
                    between_lows = [
                        sl for sl in swing_lows
                        if prev_sh["index"] < sl["index"] < curr_sh["index"]
                    ]

                    if not between_lows:
                        continue

                    lowest_low = min(between_lows, key=lambda x: x["price"])

                    future_data = data.iloc[curr_sh["index"] + 1:]
                    for j, (_, candle) in enumerate(future_data.iterrows()):
                        if float(candle["close"]) < lowest_low["price"]:
                            choch_events.append({
                                "type": "BEARISH_CHOCH",
                                "direction": "BEARISH",
                                "broken_level": float(lowest_low["price"]),
                                "break_index": curr_sh["index"] + j + 1,
                                "prev_high": float(prev_sh["price"]),
                                "curr_high": float(curr_sh["price"]),
                                "break_close": float(candle["close"]),
                                "strength": float(
                                    (lowest_low["price"] - float(candle["close"])) / lowest_low["price"] * 100
                                ),
                                "confirmed": True,
                                "higher_timeframe_significance": float(prev_sh["price"] - curr_sh["price"]) / prev_sh["price"] > 0.01,
                            })
                            break

            for i in range(1, len(swing_lows)):
                prev_sl = swing_lows[i - 1]
                curr_sl = swing_lows[i]

                if curr_sl["price"] > prev_sl["price"]:
                    between_highs = [
                        sh for sh in swing_highs
                        if prev_sl["index"] < sh["index"] < curr_sl["index"]
                    ]

                    if not between_highs:
                        continue

                    highest_high = max(between_highs, key=lambda x: x["price"])

                    future_data = data.iloc[curr_sl["index"] + 1:]
                    for j, (_, candle) in enumerate(future_data.iterrows()):
                        if float(candle["close"]) > highest_high["price"]:
                            choch_events.append({
                                "type": "BULLISH_CHOCH",
                                "direction": "BULLISH",
                                "broken_level": float(highest_high["price"]),
                                "break_index": curr_sl["index"] + j + 1,
                                "prev_low": float(prev_sl["price"]),
                                "curr_low": float(curr_sl["price"]),
                                "break_close": float(candle["close"]),
                                "strength": float(
                                    (float(candle["close"]) - highest_high["price"]) / highest_high["price"] * 100
                                ),
                                "confirmed": True,
                                "higher_timeframe_significance": float(curr_sl["price"] - prev_sl["price"]) / prev_sl["price"] > 0.01,
                            })
                            break

            return sorted(choch_events, key=lambda x: x["break_index"], reverse=True)
        except Exception as e:
            logger.error(f"Error detecting CHOCH: {e}")
            return []

    @staticmethod
    def get_market_structure(
        df: pd.DataFrame,
        lookback: int = 100,
    ) -> Dict[str, Any]:
        try:
            swing_highs = BOSCHOCHDetector.find_swing_highs(df.iloc[-lookback:])
            swing_lows = BOSCHOCHDetector.find_swing_lows(df.iloc[-lookback:])

            if len(swing_highs) < 2 or len(swing_lows) < 2:
                return {"structure": "UNDEFINED", "trend": "NEUTRAL"}

            recent_highs = sorted(swing_highs, key=lambda x: x["index"])[-3:]
            recent_lows = sorted(swing_lows, key=lambda x: x["index"])[-3:]

            hh = len(recent_highs) >= 2 and all(
                recent_highs[i]["price"] > recent_highs[i - 1]["price"]
                for i in range(1, len(recent_highs))
            )
            hl = len(recent_lows) >= 2 and all(
                recent_lows[i]["price"] > recent_lows[i - 1]["price"]
                for i in range(1, len(recent_lows))
            )
            lh = len(recent_highs) >= 2 and all(
                recent_highs[i]["price"] < recent_highs[i - 1]["price"]
                for i in range(1, len(recent_highs))
            )
            ll = len(recent_lows) >= 2 and all(
                recent_lows[i]["price"] < recent_lows[i - 1]["price"]
                for i in range(1, len(recent_lows))
            )

            if hh and hl:
                structure = "BULLISH"
                trend = "UPTREND"
            elif lh and ll:
                structure = "BEARISH"
                trend = "DOWNTREND"
            elif hh and ll:
                structure = "DISTRIBUTION"
                trend = "NEUTRAL"
            elif lh and hl:
                structure = "ACCUMULATION"
                trend = "NEUTRAL"
            else:
                structure = "RANGING"
                trend = "NEUTRAL"

            return {
                "structure": structure,
                "trend": trend,
                "higher_highs": hh,
                "higher_lows": hl,
                "lower_highs": lh,
                "lower_lows": ll,
                "recent_swing_highs": [
                    {"price": sh["price"], "index": sh["index"]}
                    for sh in recent_highs
                ],
                "recent_swing_lows": [
                    {"price": sl["price"], "index": sl["index"]}
                    for sl in recent_lows
                ],
            }
        except Exception as e:
            logger.error(f"Error getting market structure: {e}")
            return {"structure": "UNDEFINED", "trend": "NEUTRAL"}

    @staticmethod
    def get_recent_bos(
        df: pd.DataFrame,
        bars: int = 10,
    ) -> Optional[Dict[str, Any]]:
        try:
            bos_events = BOSCHOCHDetector.detect_bos(df)
            recent = [b for b in bos_events if b["break_index"] >= len(df) - bars - 1]
            if recent:
                return recent[0]
            return None
        except Exception as e:
            logger.error(f"Error getting recent BOS: {e}")
            return None

    @staticmethod
    def get_recent_choch(
        df: pd.DataFrame,
        bars: int = 15,
    ) -> Optional[Dict[str, Any]]:
        try:
            choch_events = BOSCHOCHDetector.detect_choch(df)
            recent = [c for c in choch_events if c["break_index"] >= len(df) - bars - 1]
            if recent:
                return recent[0]
            return None
        except Exception as e:
            logger.error(f"Error getting recent CHOCH: {e}")
            return None

    @staticmethod
    def get_signal(df: pd.DataFrame) -> Dict[str, Any]:
        try:
            market_structure = BOSCHOCHDetector.get_market_structure(df)
            recent_bos = BOSCHOCHDetector.get_recent_bos(df)
            recent_choch = BOSCHOCHDetector.get_recent_choch(df)

            bos_events = BOSCHOCHDetector.detect_bos(df)
            choch_events = BOSCHOCHDetector.detect_choch(df)

            recent_bos_list = [b for b in bos_events if b["break_index"] >= len(df) - 10]
            recent_choch_list = [c for c in choch_events if c["break_index"] >= len(df) - 15]

            bullish_bos = any(b["direction"] == "BULLISH" for b in recent_bos_list)
            bearish_bos = any(b["direction"] == "BEARISH" for b in recent_bos_list)
            bullish_choch = any(c["direction"] == "BULLISH" for c in recent_choch_list)
            bearish_choch = any(c["direction"] == "BEARISH" for c in recent_choch_list)

            structure = market_structure.get("structure", "UNDEFINED")

            if bullish_choch or (bullish_bos and structure == "BULLISH"):
                signal = "BULLISH"
            elif bearish_choch or (bearish_bos and structure == "BEARISH"):
                signal = "BEARISH"
            elif structure == "BULLISH":
                signal = "BULLISH"
            elif structure == "BEARISH":
                signal = "BEARISH"
            else:
                signal = "NEUTRAL"

            choch_confirmation = bullish_choch or bearish_choch
            bos_confirmation = bullish_bos or bearish_bos

            return {
                "signal": signal,
                "market_structure": market_structure,
                "recent_bos": recent_bos,
                "recent_choch": recent_choch,
                "bullish_bos": bullish_bos,
                "bearish_bos": bearish_bos,
                "bullish_choch": bullish_choch,
                "bearish_choch": bearish_choch,
                "bos_confirmation": bos_confirmation,
                "choch_confirmation": choch_confirmation,
                "confirmation": bos_confirmation or choch_confirmation,
                "structure": structure,
            }
        except Exception as e:
            logger.error(f"Error getting BOS/CHOCH signal: {e}")
            return {
                "signal": "NEUTRAL",
                "confirmation": False,
                "structure": "UNDEFINED",
            }


__all__ = ["BOSCHOCHDetector"]

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from utils.logger import logger


class PremiumDiscountZones:

    @staticmethod
    def get_range(
        df: pd.DataFrame,
        lookback: int = 50,
    ) -> Dict[str, float]:
        try:
            data = df.iloc[-lookback:]
            swing_high = float(data["high"].max())
            swing_low = float(data["low"].min())
            mid = (swing_high + swing_low) / 2
            total_range = swing_high - swing_low
            quarter = total_range / 4

            premium_start = mid
            premium_end = swing_high
            discount_start = swing_low
            discount_end = mid
            equilibrium_upper = mid + (total_range * 0.1)
            equilibrium_lower = mid - (total_range * 0.1)

            optimal_entry_bull_top = mid - (total_range * 0.1)
            optimal_entry_bull_bottom = swing_low + (total_range * 0.25)
            optimal_entry_bear_bottom = mid + (total_range * 0.1)
            optimal_entry_bear_top = swing_high - (total_range * 0.25)

            return {
                "swing_high": round(swing_high, 8),
                "swing_low": round(swing_low, 8),
                "mid": round(mid, 8),
                "total_range": round(total_range, 8),
                "premium_start": round(premium_start, 8),
                "premium_end": round(premium_end, 8),
                "discount_start": round(discount_start, 8),
                "discount_end": round(discount_end, 8),
                "equilibrium_upper": round(equilibrium_upper, 8),
                "equilibrium_lower": round(equilibrium_lower, 8),
                "optimal_entry_bull_top": round(optimal_entry_bull_top, 8),
                "optimal_entry_bull_bottom": round(optimal_entry_bull_bottom, 8),
                "optimal_entry_bear_top": round(optimal_entry_bear_top, 8),
                "optimal_entry_bear_bottom": round(optimal_entry_bear_bottom, 8),
                "fib_236": round(swing_high - total_range * 0.236, 8),
                "fib_382": round(swing_high - total_range * 0.382, 8),
                "fib_500": round(swing_high - total_range * 0.500, 8),
                "fib_618": round(swing_high - total_range * 0.618, 8),
                "fib_786": round(swing_high - total_range * 0.786, 8),
            }
        except Exception as e:
            logger.error(f"Error getting premium/discount range: {e}")
            return {}

    @staticmethod
    def classify_price_zone(
        price: float,
        zone_data: Dict[str, float],
    ) -> Dict[str, Any]:
        try:
            if not zone_data:
                return {"zone": "UNKNOWN", "position_pct": 50.0}

            swing_high = zone_data.get("swing_high", price)
            swing_low = zone_data.get("swing_low", price)
            mid = zone_data.get("mid", price)
            total_range = zone_data.get("total_range", 1.0)
            eq_upper = zone_data.get("equilibrium_upper", mid)
            eq_lower = zone_data.get("equilibrium_lower", mid)

            if total_range == 0:
                return {"zone": "UNKNOWN", "position_pct": 50.0}

            position_pct = ((price - swing_low) / total_range) * 100

            if price >= swing_high * 0.998:
                zone = "EXTREME_PREMIUM"
            elif price >= eq_upper:
                zone = "PREMIUM"
            elif eq_lower <= price <= eq_upper:
                zone = "EQUILIBRIUM"
            elif price <= swing_low * 1.002:
                zone = "EXTREME_DISCOUNT"
            else:
                zone = "DISCOUNT"

            oeb_top = zone_data.get("optimal_entry_bull_top", mid)
            oeb_bottom = zone_data.get("optimal_entry_bull_bottom", swing_low)
            oes_bottom = zone_data.get("optimal_entry_bear_bottom", mid)
            oes_top = zone_data.get("optimal_entry_bear_top", swing_high)

            in_optimal_bull_entry = oeb_bottom <= price <= oeb_top
            in_optimal_bear_entry = oes_bottom <= price <= oes_top

            near_fib_618 = abs(price - zone_data.get("fib_618", 0)) / price < 0.005
            near_fib_382 = abs(price - zone_data.get("fib_382", 0)) / price < 0.005
            near_fib_500 = abs(price - zone_data.get("fib_500", 0)) / price < 0.005

            return {
                "zone": zone,
                "position_pct": round(position_pct, 2),
                "is_premium": price > mid,
                "is_discount": price < mid,
                "is_equilibrium": eq_lower <= price <= eq_upper,
                "in_optimal_bull_entry": in_optimal_bull_entry,
                "in_optimal_bear_entry": in_optimal_bear_entry,
                "near_fib_618": near_fib_618,
                "near_fib_382": near_fib_382,
                "near_fib_500": near_fib_500,
                "distance_from_mid_pct": round(abs(price - mid) / mid * 100, 4),
                "distance_from_high_pct": round((swing_high - price) / swing_high * 100, 4),
                "distance_from_low_pct": round((price - swing_low) / swing_low * 100, 4),
            }
        except Exception as e:
            logger.error(f"Error classifying price zone: {e}")
            return {"zone": "UNKNOWN", "position_pct": 50.0}

    @staticmethod
    def get_institutional_levels(
        df: pd.DataFrame,
        lookback: int = 200,
    ) -> List[Dict[str, Any]]:
        try:
            data = df.iloc[-lookback:]
            levels = []
            close = float(df.iloc[-1]["close"])

            weekly_high = float(data["high"].iloc[-7:].max()) if len(data) >= 7 else float(data["high"].max())
            weekly_low = float(data["low"].iloc[-7:].min()) if len(data) >= 7 else float(data["low"].min())
            monthly_high = float(data["high"].max())
            monthly_low = float(data["low"].min())

            levels.append({"type": "WEEKLY_HIGH", "price": weekly_high, "significance": "HIGH"})
            levels.append({"type": "WEEKLY_LOW", "price": weekly_low, "significance": "HIGH"})
            levels.append({"type": "MONTHLY_HIGH", "price": monthly_high, "significance": "EXTREME"})
            levels.append({"type": "MONTHLY_LOW", "price": monthly_low, "significance": "EXTREME"})

            round_levels = []
            magnitude = 10 ** (len(str(int(close))) - 2)
            for multiplier in range(
                int(monthly_low / magnitude) - 1,
                int(monthly_high / magnitude) + 2,
            ):
                round_level = multiplier * magnitude
                if monthly_low <= round_level <= monthly_high:
                    distance_pct = abs(close - round_level) / close * 100
                    round_levels.append({
                        "type": "ROUND_NUMBER",
                        "price": float(round_level),
                        "significance": "MEDIUM" if distance_pct > 1 else "HIGH",
                        "distance_pct": round(distance_pct, 4),
                    })

            levels.extend(round_levels[:10])

            for level in levels:
                level["price"] = round(level["price"], 8)
                level["distance_from_close"] = round(abs(close - level["price"]) / close * 100, 4)

            return sorted(levels, key=lambda x: x["distance_from_close"])
        except Exception as e:
            logger.error(f"Error getting institutional levels: {e}")
            return []

    @staticmethod
    def detect_supply_zones(
        df: pd.DataFrame,
        lookback: int = 100,
        min_drop_pct: float = 0.5,
    ) -> List[Dict[str, Any]]:
        try:
            data = df.iloc[-lookback:].copy().reset_index(drop=True)
            supply_zones = []

            for i in range(2, len(data) - 2):
                candle = data.iloc[i]
                high_c = float(candle["high"])
                low_c = float(candle["low"])
                open_c = float(candle["open"])
                close_c = float(candle["close"])

                is_bearish = close_c < open_c
                if not is_bearish:
                    continue

                next_candles = data.iloc[i + 1:i + 4]
                drop = float(next_candles["low"].min())
                drop_pct = (high_c - drop) / high_c * 100

                if drop_pct < min_drop_pct:
                    continue

                prev_candle = data.iloc[i - 1]
                base_high = max(float(prev_candle["high"]), high_c)
                base_low = min(float(prev_candle["low"]), low_c)

                future_data = data.iloc[i + 1:]
                is_tested = any(
                    float(c["high"]) >= base_low
                    for _, c in future_data.iterrows()
                )
                is_broken = any(
                    float(c["close"]) > base_high
                    for _, c in future_data.iterrows()
                )

                supply_zones.append({
                    "type": "SUPPLY",
                    "top": float(base_high),
                    "bottom": float(base_low),
                    "mid": float((base_high + base_low) / 2),
                    "index": i,
                    "drop_pct": float(drop_pct),
                    "is_tested": is_tested,
                    "is_broken": is_broken,
                    "strength": float(drop_pct * (1 - int(is_tested) * 0.3)),
                })

            active_supply = [z for z in supply_zones if not z["is_broken"]]
            return sorted(active_supply, key=lambda x: x["strength"], reverse=True)
        except Exception as e:
            logger.error(f"Error detecting supply zones: {e}")
            return []

    @staticmethod
    def detect_demand_zones(
        df: pd.DataFrame,
        lookback: int = 100,
        min_rise_pct: float = 0.5,
    ) -> List[Dict[str, Any]]:
        try:
            data = df.iloc[-lookback:].copy().reset_index(drop=True)
            demand_zones = []

            for i in range(2, len(data) - 2):
                candle = data.iloc[i]
                high_c = float(candle["high"])
                low_c = float(candle["low"])
                open_c = float(candle["open"])
                close_c = float(candle["close"])

                is_bullish = close_c > open_c
                if not is_bullish:
                    continue

                next_candles = data.iloc[i + 1:i + 4]
                rise = float(next_candles["high"].max())
                rise_pct = (rise - low_c) / low_c * 100

                if rise_pct < min_rise_pct:
                    continue

                prev_candle = data.iloc[i - 1]
                base_high = max(float(prev_candle["high"]), high_c)
                base_low = min(float(prev_candle["low"]), low_c)

                future_data = data.iloc[i + 1:]
                is_tested = any(
                    float(c["low"]) <= base_high
                    for _, c in future_data.iterrows()
                )
                is_broken = any(
                    float(c["close"]) < base_low
                    for _, c in future_data.iterrows()
                )

                demand_zones.append({
                    "type": "DEMAND",
                    "top": float(base_high),
                    "bottom": float(base_low),
                    "mid": float((base_high + base_low) / 2),
                    "index": i,
                    "rise_pct": float(rise_pct),
                    "is_tested": is_tested,
                    "is_broken": is_broken,
                    "strength": float(rise_pct * (1 - int(is_tested) * 0.3)),
                })

            active_demand = [z for z in demand_zones if not z["is_broken"]]
            return sorted(active_demand, key=lambda x: x["strength"], reverse=True)
        except Exception as e:
            logger.error(f"Error detecting demand zones: {e}")
            return []

    @staticmethod
    def get_nearest_zones(
        df: pd.DataFrame,
        lookback: int = 100,
    ) -> Dict[str, Any]:
        try:
            close = float(df.iloc[-1]["close"])

            supply_zones = PremiumDiscountZones.detect_supply_zones(df, lookback)
            demand_zones = PremiumDiscountZones.detect_demand_zones(df, lookback)

            supply_above = [z for z in supply_zones if z["bottom"] > close]
            demand_below = [z for z in demand_zones if z["top"] < close]

            inside_supply = [z for z in supply_zones if z["bottom"] <= close <= z["top"]]
            inside_demand = [z for z in demand_zones if z["bottom"] <= close <= z["top"]]

            nearest_supply = (
                min(supply_above, key=lambda x: x["bottom"])
                if supply_above else None
            )
            nearest_demand = (
                max(demand_below, key=lambda x: x["top"])
                if demand_below else None
            )

            return {
                "supply_zones": supply_zones[:5],
                "demand_zones": demand_zones[:5],
                "nearest_supply": nearest_supply,
                "nearest_demand": nearest_demand,
                "inside_supply": inside_supply[0] if inside_supply else None,
                "inside_demand": inside_demand[0] if inside_demand else None,
                "in_supply_zone": len(inside_supply) > 0,
                "in_demand_zone": len(inside_demand) > 0,
            }
        except Exception as e:
            logger.error(f"Error getting nearest zones: {e}")
            return {
                "supply_zones": [],
                "demand_zones": [],
                "nearest_supply": None,
                "nearest_demand": None,
                "inside_supply": None,
                "inside_demand": None,
                "in_supply_zone": False,
                "in_demand_zone": False,
            }

    @staticmethod
    def get_signal(df: pd.DataFrame) -> Dict[str, Any]:
        try:
            close = float(df.iloc[-1]["close"])
            zone_data = PremiumDiscountZones.get_range(df)
            zone_class = PremiumDiscountZones.classify_price_zone(close, zone_data)
            nearest_zones = PremiumDiscountZones.get_nearest_zones(df)
            inst_levels = PremiumDiscountZones.get_institutional_levels(df)

            in_discount = zone_class.get("is_discount", False)
            in_premium = zone_class.get("is_premium", False)
            in_equilibrium = zone_class.get("is_equilibrium", False)
            in_demand_zone = nearest_zones.get("in_demand_zone", False)
            in_supply_zone = nearest_zones.get("in_supply_zone", False)
            optimal_bull = zone_class.get("in_optimal_bull_entry", False)
            optimal_bear = zone_class.get("in_optimal_bear_entry", False)

            near_fib = (
                zone_class.get("near_fib_618", False) or
                zone_class.get("near_fib_382", False) or
                zone_class.get("near_fib_500", False)
            )

            if in_discount and optimal_bull or (in_demand_zone and in_discount):
                signal = "STRONG_BULLISH"
            elif in_discount or in_demand_zone or optimal_bull:
                signal = "BULLISH"
            elif in_premium and optimal_bear or (in_supply_zone and in_premium):
                signal = "STRONG_BEARISH"
            elif in_premium or in_supply_zone or optimal_bear:
                signal = "BEARISH"
            else:
                signal = "NEUTRAL"

            return {
                "signal": signal,
                "zone": zone_class.get("zone", "UNKNOWN"),
                "position_pct": zone_class.get("position_pct", 50.0),
                "in_discount": in_discount,
                "in_premium": in_premium,
                "in_equilibrium": in_equilibrium,
                "in_demand_zone": in_demand_zone,
                "in_supply_zone": in_supply_zone,
                "optimal_bull_entry": optimal_bull,
                "optimal_bear_entry": optimal_bear,
                "near_fibonacci": near_fib,
                "nearest_supply": nearest_zones.get("nearest_supply"),
                "nearest_demand": nearest_zones.get("nearest_demand"),
                "institutional_levels": inst_levels[:5],
                "range_data": zone_data,
                "confirmation": in_demand_zone or in_supply_zone or optimal_bull or optimal_bear,
            }
        except Exception as e:
            logger.error(f"Error getting zones signal: {e}")
            return {"signal": "NEUTRAL", "confirmation": False, "zone": "UNKNOWN"}


__all__ = ["PremiumDiscountZones"]

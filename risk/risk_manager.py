import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple, List
from config.settings import settings
from utils.logger import logger


class RiskManager:

    def __init__(self):
        self.atr_sl_multiplier = settings.ATR_SL_MULTIPLIER
        self.atr_tp1_multiplier = settings.ATR_TP1_MULTIPLIER
        self.atr_tp2_multiplier = settings.ATR_TP2_MULTIPLIER
        self.atr_tp3_multiplier = settings.ATR_TP3_MULTIPLIER
        self.min_rr = settings.MIN_RISK_REWARD
        self.max_risk_pct = settings.MAX_RISK_PER_TRADE
        self.default_risk_pct = settings.DEFAULT_RISK_PERCENT
        self.default_leverage = settings.DEFAULT_LEVERAGE

    def calculate_levels(
        self,
        direction: str,
        entry: float,
        atr_data: Dict[str, Any],
        df: Optional[pd.DataFrame] = None,
        smc_signals: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        try:
            atr = atr_data.get("value", 0.0)
            if atr <= 0 and df is not None:
                atr = self._calculate_atr(df)
            if atr <= 0:
                atr = entry * 0.01

            sl_levels = self._get_smc_sl_level(
                direction, entry, atr, smc_signals
            )
            stop_loss = sl_levels.get("stop_loss", 0.0)
            sl_reason = sl_levels.get("reason", "ATR Based")

            if stop_loss <= 0:
                if direction == "LONG":
                    stop_loss = entry - (atr * self.atr_sl_multiplier)
                else:
                    stop_loss = entry + (atr * self.atr_sl_multiplier)

            sl_distance = abs(entry - stop_loss)
            if sl_distance <= 0:
                logger.warning(f"Zero SL distance for entry={entry}")
                return None

            if direction == "LONG":
                tp1 = entry + (sl_distance * self.atr_tp1_multiplier)
                tp2 = entry + (sl_distance * self.atr_tp2_multiplier)
                tp3 = entry + (sl_distance * self.atr_tp3_multiplier)
            else:
                tp1 = entry - (sl_distance * self.atr_tp1_multiplier)
                tp2 = entry - (sl_distance * self.atr_tp2_multiplier)
                tp3 = entry - (sl_distance * self.atr_tp3_multiplier)

            tp_levels = self._refine_tp_levels(
                direction, entry, tp1, tp2, tp3,
                atr, smc_signals
            )
            tp1 = tp_levels.get("tp1", tp1)
            tp2 = tp_levels.get("tp2", tp2)
            tp3 = tp_levels.get("tp3", tp3)

            rr_tp2 = abs(tp2 - entry) / sl_distance if sl_distance > 0 else 0.0

            if rr_tp2 < self.min_rr:
                logger.debug(f"RR too low: {rr_tp2:.2f} < {self.min_rr}")
                return None

            sl_pct = (sl_distance / entry) * 100
            tp1_pct = abs(tp1 - entry) / entry * 100
            tp2_pct = abs(tp2 - entry) / entry * 100
            tp3_pct = abs(tp3 - entry) / entry * 100

            return {
                "stop_loss": round(stop_loss, 8),
                "tp1": round(tp1, 8),
                "tp2": round(tp2, 8),
                "tp3": round(tp3, 8),
                "risk_reward": round(rr_tp2, 2),
                "rr_tp1": round(abs(tp1 - entry) / sl_distance, 2),
                "rr_tp2": round(rr_tp2, 2),
                "rr_tp3": round(abs(tp3 - entry) / sl_distance, 2),
                "sl_distance": round(sl_distance, 8),
                "sl_pct": round(sl_pct, 4),
                "tp1_pct": round(tp1_pct, 4),
                "tp2_pct": round(tp2_pct, 4),
                "tp3_pct": round(tp3_pct, 4),
                "atr": round(atr, 8),
                "sl_reason": sl_reason,
            }
        except Exception as e:
            logger.error(f"Error calculating risk levels: {e}")
            return None

    def _get_smc_sl_level(
        self,
        direction: str,
        entry: float,
        atr: float,
        smc_signals: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        try:
            if smc_signals is None:
                return {"stop_loss": 0.0, "reason": "ATR Based"}

            ob = smc_signals.get("order_blocks", {})
            fvg = smc_signals.get("fair_value_gap", {})
            liq = smc_signals.get("liquidity", {})
            zones = smc_signals.get("zones", {})
            bos = smc_signals.get("bos_choch", {})

            sl_candidates = []

            if direction == "LONG":
                if ob.get("at_bullish_ob") and ob.get("bullish_ob"):
                    ob_data = ob["bullish_ob"]
                    sl_candidate = ob_data.get("bottom", 0.0) - (atr * 0.3)
                    if sl_candidate > 0 and sl_candidate < entry:
                        sl_candidates.append({
                            "stop_loss": sl_candidate,
                            "reason": "Below Bullish Order Block",
                            "distance": entry - sl_candidate,
                        })

                if fvg.get("in_bullish_fvg") and fvg.get("current_bull_fvg"):
                    fvg_data = fvg["current_bull_fvg"]
                    sl_candidate = fvg_data.get("bottom", 0.0) - (atr * 0.2)
                    if sl_candidate > 0 and sl_candidate < entry:
                        sl_candidates.append({
                            "stop_loss": sl_candidate,
                            "reason": "Below Bullish FVG",
                            "distance": entry - sl_candidate,
                        })

                liq_level = liq.get("nearest_low_liquidity", {})
                if liq_level:
                    sl_candidate = liq_level.get("level", 0.0) - (atr * 0.3)
                    if sl_candidate > 0 and sl_candidate < entry:
                        sl_candidates.append({
                            "stop_loss": sl_candidate,
                            "reason": "Below Liquidity Low",
                            "distance": entry - sl_candidate,
                        })

                nearest_demand = zones.get("nearest_demand", {}) if zones else {}
                if nearest_demand:
                    sl_candidate = nearest_demand.get("bottom", 0.0) - (atr * 0.2)
                    if sl_candidate > 0 and sl_candidate < entry:
                        sl_candidates.append({
                            "stop_loss": sl_candidate,
                            "reason": "Below Demand Zone",
                            "distance": entry - sl_candidate,
                        })

                structure = bos.get("market_structure", {})
                recent_lows = structure.get("recent_swing_lows", [])
                if recent_lows:
                    lowest_recent = min(l["price"] for l in recent_lows)
                    sl_candidate = lowest_recent - (atr * 0.2)
                    if sl_candidate > 0 and sl_candidate < entry:
                        sl_candidates.append({
                            "stop_loss": sl_candidate,
                            "reason": "Below Recent Swing Low",
                            "distance": entry - sl_candidate,
                        })

            else:
                if ob.get("at_bearish_ob") and ob.get("bearish_ob"):
                    ob_data = ob["bearish_ob"]
                    sl_candidate = ob_data.get("top", 0.0) + (atr * 0.3)
                    if sl_candidate > entry:
                        sl_candidates.append({
                            "stop_loss": sl_candidate,
                            "reason": "Above Bearish Order Block",
                            "distance": sl_candidate - entry,
                        })

                if fvg.get("in_bearish_fvg") and fvg.get("current_bear_fvg"):
                    fvg_data = fvg["current_bear_fvg"]
                    sl_candidate = fvg_data.get("top", 0.0) + (atr * 0.2)
                    if sl_candidate > entry:
                        sl_candidates.append({
                            "stop_loss": sl_candidate,
                            "reason": "Above Bearish FVG",
                            "distance": sl_candidate - entry,
                        })

                liq_level = liq.get("nearest_high_liquidity", {})
                if liq_level:
                    sl_candidate = liq_level.get("level", 0.0) + (atr * 0.3)
                    if sl_candidate > entry:
                        sl_candidates.append({
                            "stop_loss": sl_candidate,
                            "reason": "Above Liquidity High",
                            "distance": sl_candidate - entry,
                        })

                nearest_supply = zones.get("nearest_supply", {}) if zones else {}
                if nearest_supply:
                    sl_candidate = nearest_supply.get("top", 0.0) + (atr * 0.2)
                    if sl_candidate > entry:
                        sl_candidates.append({
                            "stop_loss": sl_candidate,
                            "reason": "Above Supply Zone",
                            "distance": sl_candidate - entry,
                        })

                structure = bos.get("market_structure", {})
                recent_highs = structure.get("recent_swing_highs", [])
                if recent_highs:
                    highest_recent = max(h["price"] for h in recent_highs)
                    sl_candidate = highest_recent + (atr * 0.2)
                    if sl_candidate > entry:
                        sl_candidates.append({
                            "stop_loss": sl_candidate,
                            "reason": "Above Recent Swing High",
                            "distance": sl_candidate - entry,
                        })

            if not sl_candidates:
                return {"stop_loss": 0.0, "reason": "ATR Based"}

            max_sl_distance = atr * self.atr_sl_multiplier * 2.5
            valid_candidates = [
                c for c in sl_candidates
                if c["distance"] <= max_sl_distance
            ]

            if not valid_candidates:
                valid_candidates = sl_candidates

            best = min(valid_candidates, key=lambda x: x["distance"])
            return {
                "stop_loss": best["stop_loss"],
                "reason": best["reason"],
            }
        except Exception as e:
            logger.error(f"Error getting SMC SL level: {e}")
            return {"stop_loss": 0.0, "reason": "ATR Based"}

    def _refine_tp_levels(
        self,
        direction: str,
        entry: float,
        tp1: float,
        tp2: float,
        tp3: float,
        atr: float,
        smc_signals: Optional[Dict[str, Any]],
    ) -> Dict[str, float]:
        try:
            if smc_signals is None:
                return {"tp1": tp1, "tp2": tp2, "tp3": tp3}

            liq = smc_signals.get("liquidity", {})
            ob = smc_signals.get("order_blocks", {})
            zones = smc_signals.get("zones", {})

            refined_tp1 = tp1
            refined_tp2 = tp2
            refined_tp3 = tp3

            if direction == "LONG":
                high_liq = liq.get("nearest_high_liquidity", {})
                if high_liq:
                    liq_level = high_liq.get("level", 0.0)
                    if entry < liq_level:
                        if abs(liq_level - tp1) / tp1 < 0.03:
                            refined_tp1 = liq_level * 0.998
                        elif abs(liq_level - tp2) / tp2 < 0.03:
                            refined_tp2 = liq_level * 0.998
                        elif abs(liq_level - tp3) / tp3 < 0.05:
                            refined_tp3 = liq_level * 0.998

                resistance_obs = ob.get("resistance_obs", [])
                if resistance_obs:
                    nearest_res = resistance_obs[0]
                    res_bottom = nearest_res.get("bottom", 0.0)
                    if entry < res_bottom < tp2:
                        refined_tp2 = res_bottom * 0.998

                nearest_supply = zones.get("nearest_supply", {}) if isinstance(zones, dict) else {}
                if isinstance(nearest_supply, dict) and nearest_supply:
                    supply_bottom = nearest_supply.get("bottom", 0.0)
                    if entry < supply_bottom < tp3:
                        refined_tp3 = supply_bottom * 0.998

            else:
                low_liq = liq.get("nearest_low_liquidity", {})
                if low_liq:
                    liq_level = low_liq.get("level", 0.0)
                    if entry > liq_level > 0:
                        if abs(liq_level - tp1) / tp1 < 0.03:
                            refined_tp1 = liq_level * 1.002
                        elif abs(liq_level - tp2) / tp2 < 0.03:
                            refined_tp2 = liq_level * 1.002
                        elif abs(liq_level - tp3) / tp3 < 0.05:
                            refined_tp3 = liq_level * 1.002

                support_obs = ob.get("support_obs", [])
                if support_obs:
                    nearest_sup = support_obs[0]
                    sup_top = nearest_sup.get("top", 0.0)
                    if tp2 < sup_top < entry:
                        refined_tp2 = sup_top * 1.002

                nearest_demand = zones.get("nearest_demand", {}) if isinstance(zones, dict) else {}
                if isinstance(nearest_demand, dict) and nearest_demand:
                    demand_top = nearest_demand.get("top", 0.0)
                    if tp3 < demand_top < entry:
                        refined_tp3 = demand_top * 1.002

            return {
                "tp1": round(refined_tp1, 8),
                "tp2": round(refined_tp2, 8),
                "tp3": round(refined_tp3, 8),
            }
        except Exception as e:
            logger.error(f"Error refining TP levels: {e}")
            return {"tp1": tp1, "tp2": tp2, "tp3": tp3}

    def _calculate_atr(
        self,
        df: pd.DataFrame,
        period: int = 14,
    ) -> float:
        try:
            high = df["high"]
            low = df["low"]
            close = df["close"]
            tr1 = high - low
            tr2 = (high - close.shift()).abs()
            tr3 = (low - close.shift()).abs()
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = true_range.ewm(span=period, adjust=False).mean()
            return float(atr.iloc[-1])
        except Exception as e:
            logger.error(f"Error calculating ATR: {e}")
            return 0.0

    def calculate_position_size(
        self,
        account_balance: float,
        entry: float,
        stop_loss: float,
        risk_pct: Optional[float] = None,
        leverage: Optional[int] = None,
    ) -> Dict[str, float]:
        try:
            risk_pct = risk_pct or self.default_risk_pct
            leverage = leverage or self.default_leverage

            risk_amount = account_balance * (risk_pct / 100)
            sl_distance = abs(entry - stop_loss)

            if sl_distance <= 0:
                return {
                    "position_size": 0.0,
                    "contracts": 0.0,
                    "risk_amount": 0.0,
                    "margin_required": 0.0,
                }

            sl_pct = (sl_distance / entry) * 100
            position_value = risk_amount / (sl_pct / 100)
            contracts = position_value / entry
            margin_required = position_value / leverage

            if margin_required > account_balance * (self.max_risk_pct / 100):
                adjusted_margin = account_balance * (self.max_risk_pct / 100)
                adjusted_position = adjusted_margin * leverage
                contracts = adjusted_position / entry
                position_value = adjusted_position
                risk_amount = position_value * (sl_pct / 100)

            return {
                "position_size": round(position_value, 2),
                "contracts": round(contracts, 6),
                "risk_amount": round(risk_amount, 2),
                "risk_pct": round(risk_pct, 4),
                "sl_pct": round(sl_pct, 4),
                "leverage": leverage,
                "margin_required": round(margin_required, 2),
                "potential_profit_tp1": round(contracts * abs(0.0), 2),
            }
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return {
                "position_size": 0.0,
                "contracts": 0.0,
                "risk_amount": 0.0,
                "margin_required": 0.0,
            }

    def calculate_pnl(
        self,
        direction: str,
        entry: float,
        exit_price: float,
        contracts: float,
        leverage: int = 10,
    ) -> Dict[str, float]:
        try:
            if direction == "LONG":
                price_change_pct = (exit_price - entry) / entry * 100
            else:
                price_change_pct = (entry - exit_price) / entry * 100

            leveraged_pnl_pct = price_change_pct * leverage
            position_value = contracts * entry
            pnl_amount = position_value * (price_change_pct / 100)

            return {
                "price_change_pct": round(price_change_pct, 4),
                "leveraged_pnl_pct": round(leveraged_pnl_pct, 4),
                "pnl_amount": round(pnl_amount, 4),
                "position_value": round(position_value, 4),
            }
        except Exception as e:
            logger.error(f"Error calculating PnL: {e}")
            return {
                "price_change_pct": 0.0,
                "leveraged_pnl_pct": 0.0,
                "pnl_amount": 0.0,
                "position_value": 0.0,
            }

    def validate_risk_parameters(
        self,
        entry: float,
        stop_loss: float,
        tp1: float,
        tp2: float,
        direction: str,
    ) -> Tuple[bool, str]:
        try:
            if entry <= 0:
                return False, "Invalid entry price"
            if stop_loss <= 0:
                return False, "Invalid stop loss price"
            if tp1 <= 0 or tp2 <= 0:
                return False, "Invalid take profit price"

            sl_distance = abs(entry - stop_loss)
            sl_pct = (sl_distance / entry) * 100

            if sl_pct > 20.0:
                return False, f"Stop loss too far: {sl_pct:.2f}%"
            if sl_pct < 0.1:
                return False, f"Stop loss too close: {sl_pct:.2f}%"

            if direction == "LONG":
                if stop_loss >= entry:
                    return False, "Stop loss must be below entry for LONG"
                if tp1 <= entry:
                    return False, "TP1 must be above entry for LONG"
                if tp2 <= tp1:
                    return False, "TP2 must be above TP1 for LONG"
            else:
                if stop_loss <= entry:
                    return False, "Stop loss must be above entry for SHORT"
                if tp1 >= entry:
                    return False, "TP1 must be below entry for SHORT"
                if tp2 >= tp1:
                    return False, "TP2 must be below TP1 for SHORT"

            rr = abs(tp2 - entry) / sl_distance
            if rr < self.min_rr:
                return False, f"Risk/reward too low: {rr:.2f}"

            return True, "Valid"
        except Exception as e:
            logger.error(f"Error validating risk parameters: {e}")
            return False, f"Validation error: {e}"

    def get_risk_summary(
        self,
        entry: float,
        stop_loss: float,
        tp1: float,
        tp2: float,
        tp3: float,
        direction: str,
        account_balance: float = 1000.0,
    ) -> Dict[str, Any]:
        try:
            sl_distance = abs(entry - stop_loss)
            sl_pct = (sl_distance / entry) * 100
            rr_tp1 = abs(tp1 - entry) / sl_distance if sl_distance > 0 else 0
            rr_tp2 = abs(tp2 - entry) / sl_distance if sl_distance > 0 else 0
            rr_tp3 = abs(tp3 - entry) / sl_distance if sl_distance > 0 else 0

            position = self.calculate_position_size(
                account_balance, entry, stop_loss
            )

            return {
                "entry": entry,
                "stop_loss": stop_loss,
                "tp1": tp1,
                "tp2": tp2,
                "tp3": tp3,
                "direction": direction,
                "sl_distance": round(sl_distance, 8),
                "sl_pct": round(sl_pct, 4),
                "rr_tp1": round(rr_tp1, 2),
                "rr_tp2": round(rr_tp2, 2),
                "rr_tp3": round(rr_tp3, 2),
                "position_size": position.get("position_size", 0.0),
                "risk_amount": position.get("risk_amount", 0.0),
                "margin_required": position.get("margin_required", 0.0),
                "max_loss": round(position.get("risk_amount", 0.0), 2),
                "max_profit_tp1": round(position.get("position_size", 0.0) * abs(tp1 - entry) / entry, 2),
                "max_profit_tp2": round(position.get("position_size", 0.0) * abs(tp2 - entry) / entry, 2),
                "max_profit_tp3": round(position.get("position_size", 0.0) * abs(tp3 - entry) / entry, 2),
            }
        except Exception as e:
            logger.error(f"Error getting risk summary: {e}")
            return {}


__all__ = ["RiskManager"]

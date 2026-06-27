import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from config.settings import settings
from utils.logger import logger


class AIScorer:

    COMPONENT_WEIGHTS = {
        "trend": 0.18,
        "momentum": 0.14,
        "volume": 0.12,
        "volatility": 0.08,
        "liquidity": 0.10,
        "risk": 0.08,
        "smc": 0.20,
        "funding_rate": 0.04,
        "open_interest": 0.04,
        "whale_activity": 0.02,
    }

    def __init__(self):
        self._score_history: List[float] = []

    async def calculate_score(
        self,
        pair: str,
        timeframe: str,
        direction: str,
        indicator_signals: Dict[str, Any],
        smc_signals: Dict[str, Any],
        confluence_score: float,
        funding_data: Optional[Dict[str, Any]] = None,
        oi_data: Optional[Dict[str, Any]] = None,
        ticker_data: Optional[Dict[str, Any]] = None,
        df: Optional[pd.DataFrame] = None,
    ) -> Dict[str, Any]:
        try:
            trend_score = self._score_trend(direction, indicator_signals)
            momentum_score = self._score_momentum(direction, indicator_signals)
            volume_score = self._score_volume(direction, indicator_signals)
            volatility_score = self._score_volatility(indicator_signals)
            liquidity_score = self._score_liquidity(direction, smc_signals)
            risk_score = self._score_risk(direction, smc_signals)
            smc_score = self._score_smc(direction, smc_signals)
            funding_score = self._score_funding_rate(direction, funding_data)
            oi_score = self._score_open_interest(direction, oi_data)
            whale_score = self._score_whale_activity(direction, ticker_data, df)

            component_scores = {
                "trend": round(trend_score, 2),
                "momentum": round(momentum_score, 2),
                "volume": round(volume_score, 2),
                "volatility": round(volatility_score, 2),
                "liquidity": round(liquidity_score, 2),
                "risk": round(risk_score, 2),
                "smc": round(smc_score, 2),
                "funding_rate": round(funding_score, 2),
                "open_interest": round(oi_score, 2),
                "whale_activity": round(whale_score, 2),
            }

            weighted_score = sum(
                component_scores[key] * self.COMPONENT_WEIGHTS[key]
                for key in self.COMPONENT_WEIGHTS
            )

            timeframe_bonus = self._get_timeframe_bonus(timeframe)
            confluence_bonus = (confluence_score / 100) * 10

            final_score = weighted_score + timeframe_bonus + confluence_bonus
            final_score = min(100.0, max(0.0, final_score))

            confidence = self._normalize_to_confidence(
                final_score,
                component_scores,
                confluence_score,
            )

            return {
                "confidence": round(confidence, 2),
                "raw_score": round(final_score, 2),
                "weighted_score": round(weighted_score, 2),
                "confluence_score": round(confluence_score, 2),
                "component_scores": component_scores,
                "timeframe_bonus": round(timeframe_bonus, 2),
                "confluence_bonus": round(confluence_bonus, 2),
                "grade": self._get_grade(confidence),
            }
        except Exception as e:
            logger.error(f"Error calculating AI score for {pair}: {e}")
            return {
                "confidence": 0.0,
                "raw_score": 0.0,
                "component_scores": {},
                "grade": "F",
            }

    def _score_trend(
        self,
        direction: str,
        indicator_signals: Dict[str, Any],
    ) -> float:
        try:
            score = 0.0
            trend = indicator_signals.get("trend", {})

            ema_trend = trend.get("ema_trend", "NEUTRAL")
            macd = trend.get("macd", {})
            adx = trend.get("adx", {})
            supertrend = trend.get("supertrend", {})

            if direction == "LONG":
                if ema_trend == "BULLISH":
                    score += 25.0
                elif ema_trend == "NEUTRAL":
                    score += 10.0

                if macd.get("bullish_cross"):
                    score += 20.0
                elif macd.get("bullish"):
                    score += 12.0
                if macd.get("above_zero"):
                    score += 8.0
                if macd.get("histogram_increasing"):
                    score += 7.0

                if adx.get("trending"):
                    adx_val = adx.get("adx", 0)
                    if adx_val >= 40:
                        score += 20.0
                    elif adx_val >= 25:
                        score += 14.0
                    if adx.get("direction") == "BULLISH":
                        score += 10.0

                if supertrend.get("just_flipped_bullish"):
                    score += 20.0
                elif supertrend.get("bullish"):
                    score += 12.0

            else:
                if ema_trend == "BEARISH":
                    score += 25.0
                elif ema_trend == "NEUTRAL":
                    score += 10.0

                if macd.get("bearish_cross"):
                    score += 20.0
                elif macd.get("bearish"):
                    score += 12.0
                if not macd.get("above_zero", True):
                    score += 8.0
                if not macd.get("histogram_increasing", True):
                    score += 7.0

                if adx.get("trending"):
                    adx_val = adx.get("adx", 0)
                    if adx_val >= 40:
                        score += 20.0
                    elif adx_val >= 25:
                        score += 14.0
                    if adx.get("direction") == "BEARISH":
                        score += 10.0

                if supertrend.get("just_flipped_bearish"):
                    score += 20.0
                elif supertrend.get("bearish"):
                    score += 12.0

            return min(100.0, score)
        except Exception as e:
            logger.error(f"Error scoring trend: {e}")
            return 50.0

    def _score_momentum(
        self,
        direction: str,
        indicator_signals: Dict[str, Any],
    ) -> float:
        try:
            score = 0.0
            momentum = indicator_signals.get("momentum", {})

            rsi = momentum.get("rsi", {})
            stoch = momentum.get("stoch_rsi", {})
            cci = momentum.get("cci", {})
            divergence = momentum.get("divergence", {})

            rsi_val = rsi.get("value", 50)

            if direction == "LONG":
                if rsi.get("oversold"):
                    score += 30.0
                elif 40 <= rsi_val <= 60:
                    score += 15.0
                elif rsi_val > 50:
                    score += 20.0
                if rsi.get("crossing_up_50"):
                    score += 15.0

                if stoch.get("bullish_cross_oversold"):
                    score += 25.0
                elif stoch.get("bullish_cross"):
                    score += 15.0
                elif stoch.get("oversold"):
                    score += 20.0

                if cci.get("oversold"):
                    score += 20.0
                elif cci.get("crossing_up_zero"):
                    score += 15.0
                elif cci.get("signal") == "BULLISH":
                    score += 10.0

                if divergence.get("bullish_divergence"):
                    score += 20.0

            else:
                if rsi.get("overbought"):
                    score += 30.0
                elif 40 <= rsi_val <= 60:
                    score += 15.0
                elif rsi_val < 50:
                    score += 20.0
                if rsi.get("crossing_down_50"):
                    score += 15.0

                if stoch.get("bearish_cross_overbought"):
                    score += 25.0
                elif stoch.get("bearish_cross"):
                    score += 15.0
                elif stoch.get("overbought"):
                    score += 20.0

                if cci.get("overbought"):
                    score += 20.0
                elif cci.get("crossing_down_zero"):
                    score += 15.0
                elif cci.get("signal") == "BEARISH":
                    score += 10.0

                if divergence.get("bearish_divergence"):
                    score += 20.0

            return min(100.0, score)
        except Exception as e:
            logger.error(f"Error scoring momentum: {e}")
            return 50.0

    def _score_volume(
        self,
        direction: str,
        indicator_signals: Dict[str, Any],
    ) -> float:
        try:
            score = 0.0
            volume = indicator_signals.get("volume", {})

            obv = volume.get("obv", {})
            mfi = volume.get("mfi", {})
            vwap = volume.get("vwap", {})
            vol = volume.get("volume", {})
            vp = volume.get("volume_profile", {})

            if direction == "LONG":
                if obv.get("bullish_cross"):
                    score += 20.0
                elif obv.get("signal") == "BULLISH":
                    score += 12.0
                if obv.get("rising"):
                    score += 8.0

                if mfi.get("oversold"):
                    score += 20.0
                elif mfi.get("signal") == "BULLISH":
                    score += 12.0
                if mfi.get("crossing_up_50"):
                    score += 10.0

                if vwap.get("signal") == "BULLISH":
                    score += 20.0
                if vwap.get("near_vwap"):
                    score += 8.0

                if vol.get("very_high_volume"):
                    score += 15.0
                elif vol.get("high_volume"):
                    score += 8.0

                if vp.get("signal") == "BULLISH":
                    score += 12.0
                if vp.get("near_poc"):
                    score += 8.0

            else:
                if obv.get("bearish_cross"):
                    score += 20.0
                elif obv.get("signal") == "BEARISH":
                    score += 12.0
                if not obv.get("rising", True):
                    score += 8.0

                if mfi.get("overbought"):
                    score += 20.0
                elif mfi.get("signal") == "BEARISH":
                    score += 12.0
                if mfi.get("crossing_down_50"):
                    score += 10.0

                if vwap.get("signal") == "BEARISH":
                    score += 20.0
                if vwap.get("near_vwap"):
                    score += 8.0

                if vol.get("very_high_volume"):
                    score += 15.0
                elif vol.get("high_volume"):
                    score += 8.0

                if vp.get("signal") == "BEARISH":
                    score += 12.0
                if vp.get("near_poc"):
                    score += 8.0

            return min(100.0, score)
        except Exception as e:
            logger.error(f"Error scoring volume: {e}")
            return 50.0

    def _score_volatility(
        self,
        indicator_signals: Dict[str, Any],
    ) -> float:
        try:
            score = 50.0
            volatility = indicator_signals.get("volatility", {})
            regime = volatility.get("regime", {})
            bb = volatility.get("bollinger", {})
            atr = volatility.get("atr", {})

            vol_regime = regime.get("regime", "NORMAL")
            if vol_regime == "NORMAL":
                score += 20.0
            elif vol_regime == "LOW":
                score += 10.0
            elif vol_regime == "HIGH":
                score += 15.0
            elif vol_regime == "EXTREME":
                score -= 30.0

            if bb.get("squeeze"):
                score += 15.0

            if not regime.get("tradeable", True):
                score -= 40.0

            atr_ratio = atr.get("ratio", 1.0)
            if 0.8 <= atr_ratio <= 1.5:
                score += 10.0
            elif atr_ratio > 2.5:
                score -= 15.0

            return min(100.0, max(0.0, score))
        except Exception as e:
            logger.error(f"Error scoring volatility: {e}")
            return 50.0

    def _score_liquidity(
        self,
        direction: str,
        smc_signals: Dict[str, Any],
    ) -> float:
        try:
            score = 0.0
            liq = smc_signals.get("liquidity", {})

            if direction == "LONG":
                if liq.get("bullish_sweep"):
                    score += 40.0
                if liq.get("bullish_grab"):
                    score += 30.0
                if liq.get("price_near_low_liquidity"):
                    score += 20.0
                if liq.get("sweep_confirmation"):
                    score += 10.0

            else:
                if liq.get("bearish_sweep"):
                    score += 40.0
                if liq.get("bearish_grab"):
                    score += 30.0
                if liq.get("price_near_high_liquidity"):
                    score += 20.0
                if liq.get("sweep_confirmation"):
                    score += 10.0

            total_pools = liq.get("total_high_pools", 0) + liq.get("total_low_pools", 0)
            if total_pools > 0:
                score += min(10.0, total_pools * 2)

            return min(100.0, score)
        except Exception as e:
            logger.error(f"Error scoring liquidity: {e}")
            return 50.0

    def _score_risk(
        self,
        direction: str,
        smc_signals: Dict[str, Any],
    ) -> float:
        try:
            score = 50.0
            bos = smc_signals.get("bos_choch", {})
            zones = smc_signals.get("zones", {})

            structure = bos.get("structure", "UNDEFINED")

            if direction == "LONG":
                if structure == "BULLISH":
                    score += 30.0
                elif structure == "BEARISH":
                    score -= 20.0
                elif structure in ("ACCUMULATION",):
                    score += 15.0

                zone_signal = zones.get("signal", "NEUTRAL") if isinstance(zones, dict) else "NEUTRAL"
                if "BULLISH" in zone_signal:
                    score += 20.0
                elif "BEARISH" in zone_signal:
                    score -= 10.0

            else:
                if structure == "BEARISH":
                    score += 30.0
                elif structure == "BULLISH":
                    score -= 20.0
                elif structure in ("DISTRIBUTION",):
                    score += 15.0

                zone_signal = zones.get("signal", "NEUTRAL") if isinstance(zones, dict) else "NEUTRAL"
                if "BEARISH" in zone_signal:
                    score += 20.0
                elif "BULLISH" in zone_signal:
                    score -= 10.0

            return min(100.0, max(0.0, score))
        except Exception as e:
            logger.error(f"Error scoring risk: {e}")
            return 50.0

    def _score_smc(
        self,
        direction: str,
        smc_signals: Dict[str, Any],
    ) -> float:
        try:
            score = 0.0

            ob = smc_signals.get("order_blocks", {})
            fvg = smc_signals.get("fair_value_gap", {})
            liq = smc_signals.get("liquidity", {})
            bos = smc_signals.get("bos_choch", {})
            breaker = smc_signals.get("breaker_blocks", {})
            zones = smc_signals.get("zones", {})

            if direction == "LONG":
                if ob.get("at_bullish_ob"):
                    score += 20.0
                if fvg.get("in_bullish_fvg"):
                    score += 15.0
                if fvg.get("bullish_fvg_stack"):
                    score += 8.0
                if liq.get("bullish_sweep"):
                    score += 18.0
                if liq.get("bullish_grab"):
                    score += 12.0
                if bos.get("bullish_choch"):
                    score += 20.0
                elif bos.get("bullish_bos"):
                    score += 12.0
                if breaker.get("at_bullish_breaker"):
                    score += 15.0
                if breaker.get("bullish_mitigation"):
                    score += 8.0
                zone_signal = zones.get("signal", "NEUTRAL") if isinstance(zones, dict) else "NEUTRAL"
                if zone_signal == "STRONG_BULLISH":
                    score += 15.0
                elif zone_signal == "BULLISH":
                    score += 10.0

            else:
                if ob.get("at_bearish_ob"):
                    score += 20.0
                if fvg.get("in_bearish_fvg"):
                    score += 15.0
                if fvg.get("bearish_fvg_stack"):
                    score += 8.0
                if liq.get("bearish_sweep"):
                    score += 18.0
                if liq.get("bearish_grab"):
                    score += 12.0
                if bos.get("bearish_choch"):
                    score += 20.0
                elif bos.get("bearish_bos"):
                    score += 12.0
                if breaker.get("at_bearish_breaker"):
                    score += 15.0
                if breaker.get("bearish_mitigation"):
                    score += 8.0
                zone_signal = zones.get("signal", "NEUTRAL") if isinstance(zones, dict) else "NEUTRAL"
                if zone_signal == "STRONG_BEARISH":
                    score += 15.0
                elif zone_signal == "BEARISH":
                    score += 10.0

            confirmations = sum([
                ob.get("confirmation", False),
                fvg.get("confirmation", False),
                liq.get("confirmation", False),
                bos.get("confirmation", False),
                breaker.get("confirmation", False),
            ])

            if confirmations >= 4:
                score += 15.0
            elif confirmations >= 3:
                score += 10.0
            elif confirmations >= 2:
                score += 5.0

            return min(100.0, score)
        except Exception as e:
            logger.error(f"Error scoring SMC: {e}")
            return 50.0

    def _score_funding_rate(
        self,
        direction: str,
        funding_data: Optional[Dict[str, Any]],
    ) -> float:
        try:
            if not funding_data:
                return 50.0

            funding_rate = funding_data.get("funding_rate", 0.0) or 0.0
            funding_pct = funding_rate * 100

            score = 50.0

            if direction == "LONG":
                if funding_pct < -0.05:
                    score += 40.0
                elif funding_pct < 0:
                    score += 20.0
                elif 0 <= funding_pct <= 0.01:
                    score += 10.0
                elif funding_pct > 0.05:
                    score -= 20.0
                elif funding_pct > 0.1:
                    score -= 35.0
            else:
                if funding_pct > 0.05:
                    score += 40.0
                elif funding_pct > 0:
                    score += 20.0
                elif -0.01 <= funding_pct <= 0:
                    score += 10.0
                elif funding_pct < -0.05:
                    score -= 20.0
                elif funding_pct < -0.1:
                    score -= 35.0

            return min(100.0, max(0.0, score))
        except Exception as e:
            logger.error(f"Error scoring funding rate: {e}")
            return 50.0

    def _score_open_interest(
        self,
        direction: str,
        oi_data: Optional[Dict[str, Any]],
    ) -> float:
        try:
            if not oi_data:
                return 50.0

            oi_value = oi_data.get("open_interest_value", 0.0) or 0.0
            score = 50.0

            if oi_value > 100_000_000:
                score += 20.0
            elif oi_value > 50_000_000:
                score += 10.0
            elif oi_value < 1_000_000:
                score -= 10.0

            return min(100.0, max(0.0, score))
        except Exception as e:
            logger.error(f"Error scoring open interest: {e}")
            return 50.0

    def _score_whale_activity(
        self,
        direction: str,
        ticker_data: Optional[Dict[str, Any]],
        df: Optional[pd.DataFrame],
    ) -> float:
        try:
            score = 50.0

            if ticker_data is None:
                return score

            volume = ticker_data.get("volume", 0.0) or 0.0
            change_pct = abs(ticker_data.get("change_pct", 0.0) or 0.0)

            if volume > 0 and change_pct > 0:
                volume_price_ratio = volume / (change_pct + 0.001)
                if volume_price_ratio > 1_000_000:
                    score += 20.0
                elif volume_price_ratio > 500_000:
                    score += 10.0

            if df is not None and len(df) >= 20:
                recent_vol = df["volume"].iloc[-5:].mean()
                avg_vol = df["volume"].iloc[-20:].mean()
                vol_ratio = recent_vol / avg_vol if avg_vol > 0 else 1.0

                if vol_ratio >= 3.0:
                    score += 25.0
                elif vol_ratio >= 2.0:
                    score += 15.0
                elif vol_ratio >= 1.5:
                    score += 8.0

                recent_candles = df.iloc[-5:]
                large_wicks = sum(
                    1 for _, c in recent_candles.iterrows()
                    if (float(c["high"]) - float(c["low"])) > (float(df["atr"].iloc[-1]) * 2 if "atr" in df.columns else 0)
                )
                if large_wicks >= 2:
                    score += 10.0

            return min(100.0, max(0.0, score))
        except Exception as e:
            logger.error(f"Error scoring whale activity: {e}")
            return 50.0

    def _get_timeframe_bonus(self, timeframe: str) -> float:
        bonuses = {
            "1m": -2.0,
            "3m": -1.0,
            "5m": 0.0,
            "15m": 2.0,
            "30m": 3.0,
            "1h": 4.0,
            "4h": 5.0,
            "1d": 6.0,
        }
        return bonuses.get(timeframe, 0.0)

    def _normalize_to_confidence(
        self,
        raw_score: float,
        component_scores: Dict[str, float],
        confluence_score: float,
    ) -> float:
        try:
            avg_component = np.mean(list(component_scores.values()))
            min_score = min(component_scores.values())
            max_score = max(component_scores.values())

            consistency_penalty = 0.0
            if min_score < 30.0:
                consistency_penalty = (30.0 - min_score) * 0.3

            weak_components = sum(1 for v in component_scores.values() if v < 40.0)
            if weak_components >= 3:
                consistency_penalty += weak_components * 2.0

            normalized = (
                raw_score * 0.50 +
                avg_component * 0.30 +
                confluence_score * 0.20
            )

            normalized -= consistency_penalty

            scaled = 85.0 + ((normalized - 60.0) / 40.0) * 15.0
            scaled = min(99.9, max(85.0, scaled)) if normalized >= 60.0 else normalized * 0.9

            return round(scaled, 2)
        except Exception as e:
            logger.error(f"Error normalizing confidence: {e}")
            return 0.0

    def _get_grade(self, confidence: float) -> str:
        if confidence >= 98:
            return "S+"
        elif confidence >= 96:
            return "S"
        elif confidence >= 94:
            return "A+"
        elif confidence >= 92:
            return "A"
        elif confidence >= 90:
            return "B+"
        elif confidence >= 85:
            return "B"
        elif confidence >= 80:
            return "C"
        else:
            return "F"

    def get_score_interpretation(self, score_data: Dict[str, Any]) -> str:
        try:
            confidence = score_data.get("confidence", 0.0)
            grade = score_data.get("grade", "F")
            component_scores = score_data.get("component_scores", {})

            weakest = min(component_scores.items(), key=lambda x: x[1]) if component_scores else ("none", 0)
            strongest = max(component_scores.items(), key=lambda x: x[1]) if component_scores else ("none", 0)

            return (
                f"Grade: {grade} | Confidence: {confidence:.1f}% | "
                f"Strongest: {strongest[0].title()} ({strongest[1]:.0f}) | "
                f"Weakest: {weakest[0].title()} ({weakest[1]:.0f})"
            )
        except Exception as e:
            logger.error(f"Error getting score interpretation: {e}")
            return "Score interpretation unavailable"


__all__ = ["AIScorer"]

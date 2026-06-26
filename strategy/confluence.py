import numpy as np
from typing import Dict, Any, List, Tuple
from utils.logger import logger


class ConfluenceAnalyzer:

    WEIGHTS = {
        "ema_trend": 8,
        "macd": 6,
        "adx": 5,
        "supertrend": 7,
        "rsi": 6,
        "stoch_rsi": 5,
        "cci": 4,
        "obv": 5,
        "mfi": 5,
        "vwap": 6,
        "volume_profile": 4,
        "atr": 3,
        "bollinger": 5,
        "ichimoku": 7,
        "pivot": 4,
        "fibonacci": 4,
        "order_blocks": 9,
        "fair_value_gap": 8,
        "liquidity": 8,
        "bos_choch": 9,
        "breaker_blocks": 7,
        "zones": 7,
        "volume_strength": 5,
        "rsi_divergence": 6,
    }

    TOTAL_WEIGHT = sum(WEIGHTS.values())

    @staticmethod
    def analyze_trend_confluence(
        indicator_signals: Dict[str, Any],
    ) -> Tuple[float, List[str], List[str]]:
        try:
            bullish_reasons = []
            bearish_reasons = []
            bullish_score = 0.0
            bearish_score = 0.0

            trend = indicator_signals.get("trend", {})
            ema_trend = trend.get("ema_trend", "NEUTRAL")
            macd = trend.get("macd", {})
            adx = trend.get("adx", {})
            supertrend = trend.get("supertrend", {})

            ema_weight = ConfluenceAnalyzer.WEIGHTS["ema_trend"]
            if ema_trend == "BULLISH":
                bullish_score += ema_weight
                bullish_reasons.append("EMA Stack Bullish (20>50>100>200)")
            elif ema_trend == "BEARISH":
                bearish_score += ema_weight
                bearish_reasons.append("EMA Stack Bearish (20<50<100<200)")

            macd_weight = ConfluenceAnalyzer.WEIGHTS["macd"]
            if macd.get("bullish_cross"):
                bullish_score += macd_weight
                bullish_reasons.append("MACD Bullish Crossover")
            elif macd.get("bearish_cross"):
                bearish_score += macd_weight
                bearish_reasons.append("MACD Bearish Crossover")
            elif macd.get("bullish"):
                bullish_score += macd_weight * 0.5
                bullish_reasons.append("MACD Bullish")
            elif macd.get("bearish"):
                bearish_score += macd_weight * 0.5
                bearish_reasons.append("MACD Bearish")

            adx_weight = ConfluenceAnalyzer.WEIGHTS["adx"]
            if adx.get("trending"):
                direction = adx.get("direction", "NEUTRAL")
                strength = adx.get("strength", "WEAK")
                multiplier = 1.0 if strength == "STRONG" else 0.7 if strength == "MODERATE" else 0.4
                if direction == "BULLISH":
                    bullish_score += adx_weight * multiplier
                    bullish_reasons.append(f"ADX Trending Bullish ({strength})")
                elif direction == "BEARISH":
                    bearish_score += adx_weight * multiplier
                    bearish_reasons.append(f"ADX Trending Bearish ({strength})")

            st_weight = ConfluenceAnalyzer.WEIGHTS["supertrend"]
            if supertrend.get("just_flipped_bullish"):
                bullish_score += st_weight
                bullish_reasons.append("Supertrend Flipped Bullish")
            elif supertrend.get("just_flipped_bearish"):
                bearish_score += st_weight
                bearish_reasons.append("Supertrend Flipped Bearish")
            elif supertrend.get("bullish"):
                bullish_score += st_weight * 0.6
                bullish_reasons.append("Supertrend Bullish")
            elif supertrend.get("bearish"):
                bearish_score += st_weight * 0.6
                bearish_reasons.append("Supertrend Bearish")

            net_score = bullish_score - bearish_score
            return net_score, bullish_reasons, bearish_reasons
        except Exception as e:
            logger.error(f"Error analyzing trend confluence: {e}")
            return 0.0, [], []

    @staticmethod
    def analyze_momentum_confluence(
        indicator_signals: Dict[str, Any],
    ) -> Tuple[float, List[str], List[str]]:
        try:
            bullish_reasons = []
            bearish_reasons = []
            bullish_score = 0.0
            bearish_score = 0.0

            momentum = indicator_signals.get("momentum", {})
            rsi = momentum.get("rsi", {})
            stoch = momentum.get("stoch_rsi", {})
            cci = momentum.get("cci", {})
            divergence = momentum.get("divergence", {})

            rsi_weight = ConfluenceAnalyzer.WEIGHTS["rsi"]
            rsi_val = rsi.get("value", 50)
            if rsi.get("oversold"):
                bullish_score += rsi_weight
                bullish_reasons.append(f"RSI Oversold ({rsi_val:.1f})")
            elif rsi.get("overbought"):
                bearish_score += rsi_weight
                bearish_reasons.append(f"RSI Overbought ({rsi_val:.1f})")
            elif rsi.get("crossing_up_50"):
                bullish_score += rsi_weight * 0.7
                bullish_reasons.append("RSI Crossed Above 50")
            elif rsi.get("crossing_down_50"):
                bearish_score += rsi_weight * 0.7
                bearish_reasons.append("RSI Crossed Below 50")
            elif rsi.get("signal") == "BULLISH":
                bullish_score += rsi_weight * 0.4
            elif rsi.get("signal") == "BEARISH":
                bearish_score += rsi_weight * 0.4

            stoch_weight = ConfluenceAnalyzer.WEIGHTS["stoch_rsi"]
            if stoch.get("bullish_cross_oversold"):
                bullish_score += stoch_weight
                bullish_reasons.append("Stoch RSI Bullish Cross in Oversold")
            elif stoch.get("bearish_cross_overbought"):
                bearish_score += stoch_weight
                bearish_reasons.append("Stoch RSI Bearish Cross in Overbought")
            elif stoch.get("bullish_cross"):
                bullish_score += stoch_weight * 0.6
                bullish_reasons.append("Stoch RSI Bullish Crossover")
            elif stoch.get("bearish_cross"):
                bearish_score += stoch_weight * 0.6
                bearish_reasons.append("Stoch RSI Bearish Crossover")

            cci_weight = ConfluenceAnalyzer.WEIGHTS["cci"]
            if cci.get("oversold"):
                bullish_score += cci_weight
                bullish_reasons.append(f"CCI Oversold ({cci.get('value', 0):.0f})")
            elif cci.get("overbought"):
                bearish_score += cci_weight
                bearish_reasons.append(f"CCI Overbought ({cci.get('value', 0):.0f})")
            elif cci.get("crossing_up_zero"):
                bullish_score += cci_weight * 0.6
                bullish_reasons.append("CCI Crossed Above Zero")
            elif cci.get("crossing_down_zero"):
                bearish_score += cci_weight * 0.6
                bearish_reasons.append("CCI Crossed Below Zero")

            div_weight = ConfluenceAnalyzer.WEIGHTS["rsi_divergence"]
            if divergence.get("bullish_divergence"):
                bullish_score += div_weight
                bullish_reasons.append("RSI Bullish Divergence")
            elif divergence.get("bearish_divergence"):
                bearish_score += div_weight
                bearish_reasons.append("RSI Bearish Divergence")

            net_score = bullish_score - bearish_score
            return net_score, bullish_reasons, bearish_reasons
        except Exception as e:
            logger.error(f"Error analyzing momentum confluence: {e}")
            return 0.0, [], []

    @staticmethod
    def analyze_volume_confluence(
        indicator_signals: Dict[str, Any],
    ) -> Tuple[float, List[str], List[str]]:
        try:
            bullish_reasons = []
            bearish_reasons = []
            bullish_score = 0.0
            bearish_score = 0.0

            volume = indicator_signals.get("volume", {})
            obv = volume.get("obv", {})
            mfi = volume.get("mfi", {})
            vwap = volume.get("vwap", {})
            vol = volume.get("volume", {})
            vp = volume.get("volume_profile", {})

            obv_weight = ConfluenceAnalyzer.WEIGHTS["obv"]
            if obv.get("bullish_cross"):
                bullish_score += obv_weight
                bullish_reasons.append("OBV Bullish Crossover")
            elif obv.get("bearish_cross"):
                bearish_score += obv_weight
                bearish_reasons.append("OBV Bearish Crossover")
            elif obv.get("signal") == "BULLISH":
                bullish_score += obv_weight * 0.5
            elif obv.get("signal") == "BEARISH":
                bearish_score += obv_weight * 0.5

            mfi_weight = ConfluenceAnalyzer.WEIGHTS["mfi"]
            if mfi.get("oversold"):
                bullish_score += mfi_weight
                bullish_reasons.append(f"MFI Oversold ({mfi.get('value', 0):.1f})")
            elif mfi.get("overbought"):
                bearish_score += mfi_weight
                bearish_reasons.append(f"MFI Overbought ({mfi.get('value', 0):.1f})")
            elif mfi.get("signal") == "BULLISH":
                bullish_score += mfi_weight * 0.4
            elif mfi.get("signal") == "BEARISH":
                bearish_score += mfi_weight * 0.4

            vwap_weight = ConfluenceAnalyzer.WEIGHTS["vwap"]
            if vwap.get("signal") == "BULLISH":
                bullish_score += vwap_weight
                bullish_reasons.append(f"Price Above VWAP ({vwap.get('distance_pct', 0):.2f}%)")
            elif vwap.get("signal") == "BEARISH":
                bearish_score += vwap_weight
                bearish_reasons.append(f"Price Below VWAP ({abs(vwap.get('distance_pct', 0)):.2f}%)")

            vol_weight = ConfluenceAnalyzer.WEIGHTS["volume_strength"]
            if vol.get("very_high_volume"):
                multiplier = 1.0
            elif vol.get("high_volume"):
                multiplier = 0.6
            else:
                multiplier = 0.2

            if vol.get("high_volume") or vol.get("very_high_volume"):
                bullish_score += vol_weight * multiplier * 0.5
                bearish_score += vol_weight * multiplier * 0.5
                if vol.get("very_high_volume"):
                    bullish_reasons.append(f"Very High Volume ({vol.get('ratio', 1):.1f}x avg)")

            vp_weight = ConfluenceAnalyzer.WEIGHTS["volume_profile"]
            if vp.get("signal") == "BULLISH":
                bullish_score += vp_weight
                bullish_reasons.append("Price Above Volume POC")
            elif vp.get("signal") == "BEARISH":
                bearish_score += vp_weight
                bearish_reasons.append("Price Below Volume POC")

            net_score = bullish_score - bearish_score
            return net_score, bullish_reasons, bearish_reasons
        except Exception as e:
            logger.error(f"Error analyzing volume confluence: {e}")
            return 0.0, [], []

    @staticmethod
    def analyze_volatility_confluence(
        indicator_signals: Dict[str, Any],
    ) -> Tuple[float, List[str], List[str]]:
        try:
            bullish_reasons = []
            bearish_reasons = []
            bullish_score = 0.0
            bearish_score = 0.0

            volatility = indicator_signals.get("volatility", {})
            bb = volatility.get("bollinger", {})

            bb_weight = ConfluenceAnalyzer.WEIGHTS["bollinger"]
            if bb.get("breakout_up"):
                bullish_score += bb_weight
                bullish_reasons.append("Bollinger Band Breakout Upward")
            elif bb.get("breakout_down"):
                bearish_score += bb_weight
                bearish_reasons.append("Bollinger Band Breakout Downward")
            elif bb.get("bounce_up"):
                bullish_score += bb_weight * 0.8
                bullish_reasons.append("Bollinger Band Bounce From Lower Band")
            elif bb.get("bounce_down"):
                bearish_score += bb_weight * 0.8
                bearish_reasons.append("Bollinger Band Bounce From Upper Band")
            elif bb.get("squeeze"):
                bullish_score += bb_weight * 0.3
                bearish_score += bb_weight * 0.3
                bullish_reasons.append("Bollinger Band Squeeze (Breakout Imminent)")

            net_score = bullish_score - bearish_score
            return net_score, bullish_reasons, bearish_reasons
        except Exception as e:
            logger.error(f"Error analyzing volatility confluence: {e}")
            return 0.0, [], []

    @staticmethod
    def analyze_ichimoku_confluence(
        indicator_signals: Dict[str, Any],
    ) -> Tuple[float, List[str], List[str]]:
        try:
            bullish_reasons = []
            bearish_reasons = []
            bullish_score = 0.0
            bearish_score = 0.0

            ichimoku_data = indicator_signals.get("ichimoku", {})
            ichi = ichimoku_data.get("ichimoku", {})
            pivot = ichimoku_data.get("pivots", {})
            fib = ichimoku_data.get("fibonacci", {})

            ichi_weight = ConfluenceAnalyzer.WEIGHTS["ichimoku"]
            ichi_signal = ichi.get("signal", "NEUTRAL")
            if ichi_signal == "STRONG_BULLISH":
                bullish_score += ichi_weight
                bullish_reasons.append("Ichimoku Strong Bullish (All Conditions)")
            elif ichi_signal == "BULLISH":
                bullish_score += ichi_weight * 0.7
                bullish_reasons.append("Ichimoku Bullish")
            elif ichi_signal == "STRONG_BEARISH":
                bearish_score += ichi_weight
                bearish_reasons.append("Ichimoku Strong Bearish (All Conditions)")
            elif ichi_signal == "BEARISH":
                bearish_score += ichi_weight * 0.7
                bearish_reasons.append("Ichimoku Bearish")

            if ichi.get("golden_cross"):
                bullish_score += ichi_weight * 0.3
                bullish_reasons.append("Ichimoku TK Golden Cross")
            elif ichi.get("dead_cross"):
                bearish_score += ichi_weight * 0.3
                bearish_reasons.append("Ichimoku TK Dead Cross")

            pivot_weight = ConfluenceAnalyzer.WEIGHTS["pivot"]
            if pivot.get("near_support"):
                bullish_score += pivot_weight
                bullish_reasons.append(f"Price Near Pivot Support ({pivot.get('nearest_level', '')})")
            elif pivot.get("near_resistance"):
                bearish_score += pivot_weight
                bearish_reasons.append(f"Price Near Pivot Resistance ({pivot.get('nearest_level', '')})")
            elif pivot.get("signal") == "BULLISH":
                bullish_score += pivot_weight * 0.4
            elif pivot.get("signal") == "BEARISH":
                bearish_score += pivot_weight * 0.4

            fib_weight = ConfluenceAnalyzer.WEIGHTS["fibonacci"]
            if fib.get("at_golden_zone"):
                bullish_score += fib_weight
                bullish_reasons.append("Price at Fibonacci Golden Zone (0.5-0.618)")
            elif fib.get("near_level"):
                if fib.get("signal") == "BULLISH":
                    bullish_score += fib_weight * 0.6
                    bullish_reasons.append(f"Near Fibonacci Level ({fib.get('nearest_level', '')})")
                else:
                    bearish_score += fib_weight * 0.6
                    bearish_reasons.append(f"Near Fibonacci Level ({fib.get('nearest_level', '')})")

            net_score = bullish_score - bearish_score
            return net_score, bullish_reasons, bearish_reasons
        except Exception as e:
            logger.error(f"Error analyzing Ichimoku confluence: {e}")
            return 0.0, [], []

    @staticmethod
    def analyze_smc_confluence(
        smc_signals: Dict[str, Any],
    ) -> Tuple[float, List[str], List[str]]:
        try:
            bullish_reasons = []
            bearish_reasons = []
            bullish_score = 0.0
            bearish_score = 0.0

            ob = smc_signals.get("order_blocks", {})
            fvg = smc_signals.get("fair_value_gap", {})
            liq = smc_signals.get("liquidity", {})
            bos = smc_signals.get("bos_choch", {})
            breaker = smc_signals.get("breaker_blocks", {})
            zones = smc_signals.get("zones", {})

            ob_weight = ConfluenceAnalyzer.WEIGHTS["order_blocks"]
            if ob.get("at_bullish_ob"):
                bullish_score += ob_weight
                bullish_reasons.append("Price at Bullish Order Block")
            elif ob.get("at_bearish_ob"):
                bearish_score += ob_weight
                bearish_reasons.append("Price at Bearish Order Block")

            fvg_weight = ConfluenceAnalyzer.WEIGHTS["fair_value_gap"]
            if fvg.get("in_bullish_fvg"):
                bullish_score += fvg_weight
                bullish_reasons.append("Price Inside Bullish FVG")
            elif fvg.get("in_bearish_fvg"):
                bearish_score += fvg_weight
                bearish_reasons.append("Price Inside Bearish FVG")
            if fvg.get("bullish_fvg_stack"):
                bullish_score += fvg_weight * 0.3
                bullish_reasons.append("Bullish FVG Stack Detected")
            elif fvg.get("bearish_fvg_stack"):
                bearish_score += fvg_weight * 0.3
                bearish_reasons.append("Bearish FVG Stack Detected")

            liq_weight = ConfluenceAnalyzer.WEIGHTS["liquidity"]
            if liq.get("bullish_sweep"):
                bullish_score += liq_weight
                bullish_reasons.append("Bullish Liquidity Sweep Detected")
            elif liq.get("bearish_sweep"):
                bearish_score += liq_weight
                bearish_reasons.append("Bearish Liquidity Sweep Detected")
            if liq.get("bullish_grab"):
                bullish_score += liq_weight * 0.7
                bullish_reasons.append("Bullish Liquidity Grab Detected")
            elif liq.get("bearish_grab"):
                bearish_score += liq_weight * 0.7
                bearish_reasons.append("Bearish Liquidity Grab Detected")

            bos_weight = ConfluenceAnalyzer.WEIGHTS["bos_choch"]

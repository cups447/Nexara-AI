import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from config.settings import settings
from utils.logger import logger
from utils.formatters import SignalFormatter
from strategy.confluence import ConfluenceAnalyzer
from risk.risk_manager import RiskManager
from ai.scorer import AIScorer


class SignalEngine:

    def __init__(self):
        self.risk_manager = RiskManager()
        self.ai_scorer = AIScorer()
        self._signal_history: Dict[str, datetime] = {}

    def _check_cooldown(self, pair: str, timeframe: str) -> bool:
        try:
            key = f"{pair}_{timeframe}"
            last_signal = self._signal_history.get(key)
            if last_signal is None:
                return True
            cooldown = timedelta(minutes=settings.SIGNAL_COOLDOWN_MINUTES)
            return datetime.utcnow() - last_signal > cooldown
        except Exception as e:
            logger.error(f"Error checking cooldown for {pair}: {e}")
            return True

    def _update_cooldown(self, pair: str, timeframe: str) -> None:
        try:
            key = f"{pair}_{timeframe}"
            self._signal_history[key] = datetime.utcnow()
        except Exception as e:
            logger.error(f"Error updating cooldown for {pair}: {e}")

    def _cleanup_cooldowns(self) -> None:
        try:
            cutoff = datetime.utcnow() - timedelta(hours=24)
            self._signal_history = {
                k: v for k, v in self._signal_history.items()
                if v > cutoff
            }
        except Exception as e:
            logger.error(f"Error cleaning up cooldowns: {e}")

    async def process_scan_result(
        self,
        scan_result: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        try:
            pair = scan_result.get("pair", "")
            timeframe = scan_result.get("timeframe", "")
            df = scan_result.get("df")
            indicator_signals = scan_result.get("indicator_signals", {})
            smc_signals = scan_result.get("smc_signals", {})
            atr_data = scan_result.get("atr_data", {})
            close = scan_result.get("close", 0.0)

            if df is None or len(df) < 100:
                return None

            if not self._check_cooldown(pair, timeframe):
                logger.debug(f"Cooldown active for {pair} {timeframe}")
                return None

            confluence = ConfluenceAnalyzer.calculate_confluence_score(
                indicator_signals,
                smc_signals,
            )

            direction = confluence.get("direction", "NEUTRAL")
            if direction == "NEUTRAL":
                return None

            confluence_score = confluence.get("score", 0.0)

            if confluence_score < 50.0:
                return None

            funding_data = scan_result.get("market_data", {}).get("funding", {})
            oi_data = scan_result.get("market_data", {}).get("open_interest", {})
            ticker_data = scan_result.get("market_data", {}).get("ticker", {})

            ai_score = await self.ai_scorer.calculate_score(
                pair=pair,
                timeframe=timeframe,
                direction=direction,
                indicator_signals=indicator_signals,
                smc_signals=smc_signals,
                confluence_score=confluence_score,
                funding_data=funding_data,
                oi_data=oi_data,
                ticker_data=ticker_data,
                df=df,
            )

            final_confidence = ai_score.get("confidence", 0.0)

            if final_confidence < settings.MIN_CONFIDENCE_SCORE:
                logger.debug(
                    f"Low confidence {pair} {timeframe}: {final_confidence:.1f}% < {settings.MIN_CONFIDENCE_SCORE}%"
                )
                return None

            risk_levels = self.risk_manager.calculate_levels(
                direction=direction,
                entry=close,
                atr_data=atr_data,
                df=df,
                smc_signals=smc_signals,
            )

            if risk_levels is None:
                logger.debug(f"Invalid risk levels for {pair} {timeframe}")
                return None

            rr = risk_levels.get("risk_reward", 0.0)
            if rr < settings.MIN_RISK_REWARD:
                logger.debug(
                    f"Low RR {pair} {timeframe}: {rr:.2f} < {settings.MIN_RISK_REWARD}"
                )
                return None

            trend_bias = ConfluenceAnalyzer.get_trend_bias(indicator_signals)
            trade_duration = self._estimate_trade_duration(timeframe)
            estimated_win_rate = self._estimate_win_rate(
                final_confidence,
                rr,
                len(confluence.get("smc_confirmations", [])),
            )

            signal = {
                "pair": pair,
                "direction": direction,
                "timeframe": timeframe,
                "entry": round(close, 8),
                "stop_loss": round(risk_levels.get("stop_loss", 0.0), 8),
                "tp1": round(risk_levels.get("tp1", 0.0), 8),
                "tp2": round(risk_levels.get("tp2", 0.0), 8),
                "tp3": round(risk_levels.get("tp3", 0.0), 8),
                "risk_reward": round(rr, 2),
                "confidence": round(final_confidence, 2),
                "trend": trend_bias,
                "reasons": confluence.get("reasons", []),
                "indicators_passed": confluence.get("indicators_passed", []),
                "smc_confirmation": confluence.get("smc_confirmations", []),
                "estimated_win_rate": round(estimated_win_rate, 2),
                "trade_duration": trade_duration,
                "confluence_score": round(confluence_score, 2),
                "ai_scores": ai_score.get("component_scores", {}),
                "component_confluence": confluence.get("component_scores", {}),
                "created_at": datetime.utcnow().isoformat(),
            }

            self._update_cooldown(pair, timeframe)
            logger.info(
                f"Signal generated: {pair} {direction} {timeframe} "
                f"conf={final_confidence:.1f}% RR={rr:.2f}"
            )

            return signal
        except Exception as e:
            logger.error(f"Error processing scan result for {scan_result.get('pair', '')}: {e}")
            return None

    async def process_scan_results(
        self,
        scan_results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        try:
            self._cleanup_cooldowns()
            signals = []
            hourly_count = self._get_hourly_signal_count()

            for result in scan_results:
                if hourly_count >= settings.MAX_SIGNALS_PER_HOUR:
                    logger.warning(f"Max signals per hour reached: {hourly_count}")
                    break

                signal = await self.process_scan_result(result)
                if signal:
                    signals.append(signal)
                    hourly_count += 1

            signals.sort(key=lambda x: x.get("confidence", 0.0), reverse=True)
            logger.info(f"Signal engine: {len(scan_results)} results → {len(signals)} signals")
            return signals
        except Exception as e:
            logger.error(f"Error processing scan results: {e}")
            return []

    def _get_hourly_signal_count(self) -> int:
        try:
            cutoff = datetime.utcnow() - timedelta(hours=1)
            count = sum(
                1 for ts in self._signal_history.values()
                if ts > cutoff
            )
            return count
        except Exception as e:
            logger.error(f"Error getting hourly signal count: {e}")
            return 0

    def _estimate_trade_duration(self, timeframe: str) -> str:
        duration_map = {
            "1m": "5-30 minutes",
            "3m": "15-60 minutes",
            "5m": "30-120 minutes",
            "15m": "1-6 hours",
            "30m": "2-12 hours",
            "1h": "4-24 hours",
            "4h": "1-5 days",
            "1d": "3-14 days",
        }
        return duration_map.get(timeframe, "Unknown")

    def _estimate_win_rate(
        self,
        confidence: float,
        risk_reward: float,
        smc_count: int,
    ) -> float:
        try:
            base_rate = 50.0
            conf_bonus = (confidence - 90.0) * 1.5
            rr_bonus = min(10.0, (risk_reward - 2.0) * 2.0)
            smc_bonus = min(10.0, smc_count * 2.5)
            win_rate = base_rate + conf_bonus + rr_bonus + smc_bonus
            return min(85.0, max(50.0, win_rate))
        except Exception

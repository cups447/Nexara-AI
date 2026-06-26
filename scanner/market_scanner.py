import asyncio
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
import pandas as pd
import ccxt.async_support as ccxt

from config.settings import settings
from utils.logger import logger
from utils.retry import retry_async, RetryConfig
from utils.rate_limiter import exchange_rate_limiter
from scanner.pair_filter import PairFilter
from indicators.trend import TrendIndicators
from indicators.momentum import MomentumIndicators
from indicators.volume import VolumeIndicators
from indicators.volatility import VolatilityIndicators
from indicators.ichimoku import IchimokuIndicators
from smc.order_blocks import OrderBlocks
from smc.fair_value_gap import FairValueGap
from smc.liquidity import LiquidityAnalysis
from smc.bos_choch import BOSCHOCHDetector
from smc.breaker_blocks import BreakerBlocks
from smc.zones import PremiumDiscountZones


class MarketScanner:

    def __init__(self):
        self.exchange = ccxt.binance(settings.get_binance_config())
        self.pair_filter = PairFilter()
        self._running = False
        self._scan_count = 0
        self._start_time = time.monotonic()
        self._last_scan_time: Optional[float] = None
        self._last_scan_duration_ms: float = 0.0
        self._pairs_scanned: int = 0
        self._signals_found: int = 0
        self._signal_callbacks: List[Callable] = []
        self._ohlcv_cache: Dict[str, Dict[str, pd.DataFrame]] = {}
        self._cache_timestamps: Dict[str, Dict[str, float]] = {}
        self._cache_ttl: Dict[str, float] = {
            "1m": 60,
            "3m": 180,
            "5m": 300,
            "15m": 900,
            "30m": 1800,
            "1h": 3600,
            "4h": 14400,
            "1d": 86400,
        }

    def add_signal_callback(self, callback: Callable) -> None:
        self._signal_callbacks.append(callback)

    async def _notify_signal(self, signal: Dict[str, Any]) -> None:
        for callback in self._signal_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(signal)
                else:
                    callback(signal)
            except Exception as e:
                logger.error(f"Error in signal callback: {e}")

    @retry_async(
        max_attempts=RetryConfig.EXCHANGE_ATTEMPTS,
        min_wait=RetryConfig.EXCHANGE_MIN_WAIT,
        max_wait=RetryConfig.EXCHANGE_MAX_WAIT,
    )
    async def fetch_ohlcv(
        self,
        pair: str,
        timeframe: str,
        limit: int = 300,
    ) -> Optional[pd.DataFrame]:
        try:
            now = time.monotonic()
            cache_key_pair = self._ohlcv_cache.get(pair, {})
            cache_ts = self._cache_timestamps.get(pair, {}).get(timeframe, 0)
            ttl = self._cache_ttl.get(timeframe, 60)

            if timeframe in cache_key_pair and (now - cache_ts) < ttl:
                return cache_key_pair[timeframe]

            await exchange_rate_limiter.wait("ohlcv")
            ohlcv = await self.exchange.fetch_ohlcv(pair, timeframe, limit=limit)

            if not ohlcv or len(ohlcv) < 50:
                logger.warning(f"Insufficient OHLCV data for {pair} {timeframe}: {len(ohlcv) if ohlcv else 0} bars")
                return None

            df = pd.DataFrame(
                ohlcv,
                columns=["timestamp", "open", "high", "low", "close", "volume"],
            )
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)
            df = df.astype(float)
            df.dropna(inplace=True)

            if pair not in self._ohlcv_cache:
                self._ohlcv_cache[pair] = {}
            if pair not in self._cache_timestamps:
                self._cache_timestamps[pair] = {}

            self._ohlcv_cache[pair][timeframe] = df
            self._cache_timestamps[pair][timeframe] = now

            return df
        except Exception as e:
            logger.error(f"Error fetching OHLCV for {pair} {timeframe}: {e}")
            return None

    async def calculate_indicators(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        try:
            df = TrendIndicators.calculate_all(df)
            df = MomentumIndicators.calculate_all(df)
            df = VolumeIndicators.calculate_all(df)
            df = VolatilityIndicators.calculate_all(df)
            df = IchimokuIndicators.calculate_all(df)
            return df
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return df

    async def get_indicator_signals(
        self,
        df: pd.DataFrame,
    ) -> Dict[str, Any]:
        try:
            trend_signals = TrendIndicators.get_all_signals(df)
            momentum_signals = MomentumIndicators.get_all_signals(df)
            volume_signals = VolumeIndicators.get_all_signals(df)
            volatility_signals = VolatilityIndicators.get_all_signals(df)
            ichimoku_signals = IchimokuIndicators.get_all_signals(df)

            return {
                "trend": trend_signals,
                "momentum": momentum_signals,
                "volume": volume_signals,
                "volatility": volatility_signals,
                "ichimoku": ichimoku_signals,
            }
        except Exception as e:
            logger.error(f"Error getting indicator signals: {e}")
            return {}

    async def get_smc_signals(
        self,
        df: pd.DataFrame,
    ) -> Dict[str, Any]:
        try:
            ob_signal = OrderBlocks.get_signal(df)
            fvg_signal = FairValueGap.get_signal(df)
            liq_signal = LiquidityAnalysis.get_signal(df)
            bos_signal = BOSCHOCHDetector.get_signal(df)
            breaker_signal = BreakerBlocks.get_signal(df)
            zone_signal = PremiumDiscountZones.get_signal(df)

            return {
                "order_blocks": ob_signal,
                "fair_value_gap": fvg_signal,
                "liquidity": liq_signal,
                "bos_choch": bos_signal,
                "breaker_blocks": breaker_signal,
                "zones": zone_signal,
            }
        except Exception as e:
            logger.error(f"Error getting SMC signals: {e}")
            return {}

    async def get_market_data(
        self,
        pair: str,
    ) -> Dict[str, Any]:
        try:
            funding_data = await self.pair_filter.get_funding_rate(pair)
            oi_data = await self.pair_filter.get_open_interest(pair)
            ticker_data = await self.pair_filter.get_ticker_data(pair)

            return {
                "funding": funding_data,
                "open_interest": oi_data,
                "ticker": ticker_data,
            }
        except Exception as e:
            logger.error(f"Error getting market data for {pair}: {e}")
            return {}

    async def scan_pair_timeframe(
        self,
        pair: str,
        timeframe: str,
    ) -> Optional[Dict[str, Any]]:
        try:
            df = await self.fetch_ohlcv(pair, timeframe)
            if df is None or len(df) < 100:
                return None

            df = await self.calculate_indicators(df)
            indicator_signals = await self.get_indicator_signals(df)
            smc_signals = await self.get_smc_signals(df)

            close = float(df.iloc[-1]["close"])
            atr_data = indicator_signals.get("volatility", {}).get("atr", {})
            volatility_regime = indicator_signals.get("volatility", {}).get("regime", {})

            if not volatility_regime.get("tradeable", True):
                logger.debug(f"Skipping {pair} {timeframe}: extreme volatility")
                return None

            return {
                "pair": pair,
                "timeframe": timeframe,
                "close": close,
                "df": df,
                "indicator_signals": indicator_signals,
                "smc_signals": smc_signals,
                "atr_data": atr_data,
                "volatility_regime": volatility_regime,
            }
        except Exception as e:
            logger.error(f"Error scanning {pair} {timeframe}: {e}")
            return None

    async def scan_pair(
        self,
        pair: str,
        timeframes: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        try:
            timeframes = timeframes or settings.PRIMARY_TIMEFRAMES
            results = []

            for timeframe in timeframes:
                result = await self.scan_pair_timeframe(pair, timeframe)
                if result:
                    results.append(result)
                await asyncio.sleep(0.1)

            return results
        except Exception as e:
            logger.error(f"Error scanning pair {pair}: {e}")
            return []

    async def scan_all_pairs(
        self,
        pairs: Optional[List[str]] = None,
        timeframes: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        try:
            scan_start = time.monotonic()

            if pairs is None:
                pairs = await self.pair_filter.get_filtered_pairs()

            if not pairs:
                logger.warning("No pairs to scan")
                return []

            timeframes = timeframes or settings.PRIMARY_TIMEFRAMES
            all_results = []
            batch_size = 10

            logger.info(f"Starting scan: {len(pairs)} pairs × {len(timeframes)} timeframes")

            for i in range(0, len(pairs), batch_size):
                batch = pairs[i:i + batch_size]
                batch_tasks = [
                    self.scan_pair(pair, timeframes)
                    for pair in batch
                ]
                batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

                for result in batch_results:
                    if isinstance(result, Exception):
                        logger.error(f"Batch scan error: {result}")
                        continue
                    if result:
                        all_results.extend(result)

                await asyncio.sleep(0.5)

            scan_duration = (time.monotonic() - scan_start) * 1000
            self._last_scan_duration_ms = scan_duration
            self._pairs_scanned = len(pairs)
            self._last_scan_time = time.monotonic()
            self._scan_count += 1

            logger.info(
                f"Scan complete: {len(pairs)} pairs, "
                f"{len(all_results)} results in {scan_duration:.0f}ms"
            )

            return all_results
        except Exception as e:
            logger.error(f"Error in scan_all_pairs: {e}")
            return []

    async def run_scan_loop(
        self,
        signal_processor_callback: Optional[Callable] = None,
    ) -> None:
        self._running = True
        self._start_time = time.monotonic()
        logger.info("Market scanner started")

        if signal_processor_callback:
            self.add_signal_callback(signal_processor_callback)

        while self._running:
            try:
                loop_start = time.monotonic()
                results = await self.scan_all_pairs()

                if results and self._signal_callbacks:
                    await self._notify_signal({
                        "type": "scan_complete",
                        "results": results,
                        "scan_count": self._scan_count,
                        "pairs_scanned": self._pairs_scanned,
                    })

                elapsed = time.monotonic() - loop_start
                sleep_time = max(0, settings.SCAN_INTERVAL_SECONDS - elapsed)

                logger.info(
                    f"Scan #{self._scan_count} done in {elapsed:.1f}s. "
                    f"Next scan in {sleep_time:.1f}s"
                )
                await asyncio.sleep(sleep_time)

            except asyncio.CancelledError:
                logger.info("Scanner loop cancelled")
                break
            except Exception as e:
                logger.error(f"Scanner loop error: {e}")
                await asyncio.sleep(10)

    def stop(self) -> None:
        self._running = False
        logger.info("Market scanner stopped")

    def get_status(self) -> Dict[str, Any]:
        uptime_seconds = time.monotonic() - self._start_time
        hours = int(uptime_seconds // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        seconds = int(uptime_seconds % 60)
        uptime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        last_scan_str = "Never"
        if self._last_scan_time:
            elapsed = time.monotonic() - self._last_scan_time
            last_scan_str = f"{elapsed:.0f}s ago"

        next_scan_str = "Unknown"
        if self._last_scan_time:
            next_in = settings.SCAN_INTERVAL_SECONDS - (time.monotonic() - self._last_scan_time)
            next_scan_str = f"in {max(0, next_in):.0f}s"

        return {
            "running": self._running,
            "scan_count": self._scan_count,
            "pairs_scanned": self._pairs_scanned,
            "signals_found": self._signals_found,
            "last_scan": last_scan_str,
            "next_scan": next_scan_str,
            "scan_duration_ms": round(self._last_scan_duration_ms, 2),
            "uptime": uptime_str,
        }

    async def close(self) -> None:
        try:
            self._running = False
            await self.exchange.close()
            await self.pair_filter.close()
            logger.info("MarketScanner closed")
        except Exception as e:
            logger.error(f"Error closing MarketScanner: {e}")


__all__ = ["MarketScanner"]

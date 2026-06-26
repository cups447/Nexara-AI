import ccxt.async_support as ccxt
from typing import List, Dict, Any, Optional
from config.settings import settings
from utils.logger import logger
from utils.retry import retry_async, RetryConfig
from utils.rate_limiter import exchange_rate_limiter


class PairFilter:

    def __init__(self):
        self.exchange = ccxt.binance(settings.get_binance_config())
        self._cached_pairs: List[str] = []
        self._cache_timestamp: float = 0.0
        self._cache_ttl: float = 300.0

    async def get_all_usdt_futures_pairs(self) -> List[str]:
        try:
            await exchange_rate_limiter.wait("ticker")
            markets = await self.exchange.load_markets()
            pairs = [
                symbol for symbol, market in markets.items()
                if (
                    market.get("quote") == "USDT"
                    and market.get("type") == "future"
                    and market.get("active", False)
                    and market.get("linear", False)
                    and not symbol.endswith("_PERP")
                )
            ]
            pairs = sorted(pairs)
            logger.info(f"Found {len(pairs)} USDT futures pairs")
            return pairs
        except Exception as e:
            logger.error(f"Error fetching USDT futures pairs: {e}")
            return []

    @retry_async(max_attempts=3, min_wait=1.0, max_wait=10.0)
    async def get_tickers(self, pairs: List[str]) -> Dict[str, Any]:
        try:
            await exchange_rate_limiter.wait("ticker")
            tickers = await self.exchange.fetch_tickers(pairs)
            return tickers
        except Exception as e:
            logger.error(f"Error fetching tickers: {e}")
            return {}

    async def filter_by_volume(
        self,
        pairs: List[str],
        min_volume_usdt: float,
    ) -> List[str]:
        try:
            tickers = await self.get_tickers(pairs)
            filtered = []

            for pair in pairs:
                ticker = tickers.get(pair, {})
                if not ticker:
                    continue

                quote_volume = ticker.get("quoteVolume", 0.0) or 0.0

                if quote_volume >= min_volume_usdt:
                    filtered.append(pair)

            filtered.sort(
                key=lambda p: tickers.get(p, {}).get("quoteVolume", 0.0),
                reverse=True,
            )

            logger.info(
                f"Volume filter: {len(pairs)} → {len(filtered)} pairs "
                f"(min volume: ${min_volume_usdt:,.0f})"
            )
            return filtered
        except Exception as e:
            logger.error(f"Error filtering pairs by volume: {e}")
            return pairs

    async def filter_by_price_change(
        self,
        pairs: List[str],
        min_change_pct: float = 0.5,
    ) -> List[str]:
        try:
            tickers = await self.get_tickers(pairs)
            filtered = []

            for pair in pairs:
                ticker = tickers.get(pair, {})
                if not ticker:
                    continue

                change_pct = abs(ticker.get("percentage", 0.0) or 0.0)

                if change_pct >= min_change_pct:
                    filtered.append(pair)

            logger.info(
                f"Price change filter: {len(pairs)} → {len(filtered)} pairs "
                f"(min change: {min_change_pct}%)"
            )
            return filtered
        except Exception as e:
            logger.error(f"Error filtering pairs by price change: {e}")
            return pairs

    async def filter_blacklisted(
        self,
        pairs: List[str],
        blacklist: Optional[List[str]] = None,
    ) -> List[str]:
        try:
            if not blacklist:
                blacklist = [
                    "USDCUSDT",
                    "BUSDUSDT",
                    "TUSDUSDT",
                    "USDTUSDT",
                    "DAIUSDT",
                    "FDUSDUSDT",
                ]

            filtered = [p for p in pairs if p not in blacklist]
            logger.info(
                f"Blacklist filter: {len(pairs)} → {len(filtered)} pairs"
            )
            return filtered
        except Exception as e:
            logger.error(f"Error filtering blacklisted pairs: {e}")
            return pairs

    async def get_top_movers(
        self,
        pairs: List[str],
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        try:
            tickers = await self.get_tickers(pairs)
            movers = []

            for pair in pairs:
                ticker = tickers.get(pair, {})
                if not ticker:
                    continue

                movers.append({
                    "pair": pair,
                    "price": ticker.get("last", 0.0),
                    "change_pct": ticker.get("percentage", 0.0),
                    "volume": ticker.get("quoteVolume", 0.0),
                    "high": ticker.get("high", 0.0),
                    "low": ticker.get("low", 0.0),
                })

            movers.sort(key=lambda x: abs(x.get("change_pct", 0.0)), reverse=True)
            return movers[:limit]
        except Exception as e:
            logger.error(f"Error getting top movers: {e}")
            return []

    async def get_ticker_data(
        self,
        pair: str,
    ) -> Optional[Dict[str, Any]]:
        try:
            await exchange_rate_limiter.wait("ticker")
            ticker = await self.exchange.fetch_ticker(pair)
            return {
                "pair": pair,
                "price": ticker.get("last", 0.0),
                "bid": ticker.get("bid", 0.0),
                "ask": ticker.get("ask", 0.0),
                "change_pct": ticker.get("percentage", 0.0),
                "volume": ticker.get("quoteVolume", 0.0),
                "high": ticker.get("high", 0.0),
                "low": ticker.get("low", 0.0),
                "open": ticker.get("open", 0.0),
                "close": ticker.get("last", 0.0),
            }
        except Exception as e:
            logger.error(f"Error getting ticker for {pair}: {e}")
            return None

    async def get_funding_rate(
        self,
        pair: str,
    ) -> Optional[Dict[str, Any]]:
        try:
            await exchange_rate_limiter.wait("funding")
            funding = await self.exchange.fetch_funding_rate(pair)
            return {
                "pair": pair,
                "funding_rate": funding.get("fundingRate", 0.0),
                "next_funding_time": funding.get("nextFundingTime"),
                "timestamp": funding.get("timestamp"),
            }
        except Exception as e:
            logger.error(f"Error getting funding rate for {pair}: {e}")
            return None

    async def get_open_interest(
        self,
        pair: str,
    ) -> Optional[Dict[str, Any]]:
        try:
            await exchange_rate_limiter.wait("oi")
            oi = await self.exchange.fetch_open_interest(pair)
            return {
                "pair": pair,
                "open_interest": oi.get("openInterest", 0.0),
                "open_interest_value": oi.get("openInterestValue", 0.0),
                "timestamp": oi.get("timestamp"),
            }
        except Exception as e:
            logger.error(f"Error getting open interest for {pair}: {e}")
            return None

    async def get_filtered_pairs(
        self,
        max_pairs: Optional[int] = None,
        min_volume: Optional[float] = None,
    ) -> List[str]:
        try:
            import time
            now = time.monotonic()

            if self._cached_pairs and (now - self._cache_timestamp) < self._cache_ttl:
                logger.debug(f"Using cached pairs: {len(self._cached_pairs)}")
                return self._cached_pairs

            max_pairs = max_pairs or settings.MAX_PAIRS_TO_SCAN
            min_volume = min_volume or settings.MIN_VOLUME_USDT

            all_pairs = await self.get_all_usdt_futures_pairs()
            if not all_pairs:
                return []

            pairs = await self.filter_blacklisted(all_pairs)
            pairs = await self.filter_by_volume(pairs, min_volume)
            pairs = pairs[:max_pairs]

            self._cached_pairs = pairs
            self._cache_timestamp = now

            logger.info(f"Final filtered pairs: {len(pairs)}")
            return pairs
        except Exception as e:
            logger.error(f"Error getting filtered pairs: {e}")
            return self._cached_pairs or []

    async def close(self) -> None:
        try:
            await self.exchange.close()
        except Exception as e:
            logger.error(f"Error closing exchange connection: {e}")


__all__ = ["PairFilter"]

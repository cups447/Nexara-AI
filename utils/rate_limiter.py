import asyncio
import time
from collections import defaultdict, deque
from typing import Dict, Optional
from utils.logger import logger


class RateLimiter:
    def __init__(
        self,
        max_requests: int = 60,
        window_seconds: float = 60.0,
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, deque] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def acquire(self, key: str = "global") -> bool:
        async with self._lock:
            now = time.monotonic()
            window_start = now - self.window_seconds
            queue = self._requests[key]

            while queue and queue[0] < window_start:
                queue.popleft()

            if len(queue) >= self.max_requests:
                oldest = queue[0]
                wait_time = self.window_seconds - (now - oldest)
                logger.warning(
                    f"Rate limit reached for key={key}. "
                    f"Waiting {wait_time:.2f}s"
                )
                return False

            queue.append(now)
            return True

    async def wait_and_acquire(self, key: str = "global") -> None:
        while True:
            async with self._lock:
                now = time.monotonic()
                window_start = now - self.window_seconds
                queue = self._requests[key]

                while queue and queue[0] < window_start:
                    queue.popleft()

                if len(queue) < self.max_requests:
                    queue.append(now)
                    return

                oldest = queue[0]
                wait_time = self.window_seconds - (now - oldest) + 0.01

            await asyncio.sleep(wait_time)

    def get_remaining(self, key: str = "global") -> int:
        now = time.monotonic()
        window_start = now - self.window_seconds
        queue = self._requests[key]

        while queue and queue[0] < window_start:
            queue.popleft()

        return max(0, self.max_requests - len(queue))

    def reset(self, key: str = "global") -> None:
        self._requests[key].clear()

    def reset_all(self) -> None:
        self._requests.clear()


class ExchangeRateLimiter:
    def __init__(self):
        self._limiters: Dict[str, RateLimiter] = {
            "ohlcv": RateLimiter(max_requests=1200, window_seconds=60.0),
            "ticker": RateLimiter(max_requests=1200, window_seconds=60.0),
            "orderbook": RateLimiter(max_requests=1200, window_seconds=60.0),
            "funding": RateLimiter(max_requests=120, window_seconds=60.0),
            "oi": RateLimiter(max_requests=120, window_seconds=60.0),
        }

    async def acquire(self, endpoint: str = "ohlcv", key: str = "global") -> bool:
        limiter = self._limiters.get(endpoint, self._limiters["ohlcv"])
        return await limiter.acquire(key)

    async def wait(self, endpoint: str = "ohlcv", key: str = "global") -> None:
        limiter = self._limiters.get(endpoint, self._limiters["ohlcv"])
        await limiter.wait_and_acquire(key)

    def get_remaining(self, endpoint: str = "ohlcv") -> int:
        limiter = self._limiters.get(endpoint, self._limiters["ohlcv"])
        return limiter.get_remaining()


class TelegramRateLimiter:
    def __init__(self):
        self._global = RateLimiter(max_requests=30, window_seconds=1.0)
        self._per_chat: Dict[str, RateLimiter] = {}

    def _get_chat_limiter(self, chat_id: str) -> RateLimiter:
        if chat_id not in self._per_chat:
            self._per_chat[chat_id] = RateLimiter(max_requests=1, window_seconds=3.0)
        return self._per_chat[chat_id]

    async def acquire(self, chat_id: str) -> bool:
        global_ok = await self._global.acquire("global")
        if not global_ok:
            return False
        chat_limiter = self._get_chat_limiter(str(chat_id))
        return await chat_limiter.acquire(str(chat_id))

    async def wait(self, chat_id: str) -> None:
        await self._global.wait_and_acquire("global")
        chat_limiter = self._get_chat_limiter(str(chat_id))
        await chat_limiter.wait_and_acquire(str(chat_id))


exchange_rate_limiter = ExchangeRateLimiter()
telegram_rate_limiter = TelegramRateLimiter()

__all__ = [
    "RateLimiter",
    "ExchangeRateLimiter",
    "TelegramRateLimiter",
    "exchange_rate_limiter",
    "telegram_rate_limiter",
]

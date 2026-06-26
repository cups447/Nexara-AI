import asyncio
from functools import wraps
from typing import Callable, Tuple, Type, Any, Optional
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log,
)
import logging
from utils.logger import logger


def retry_async(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            attempt = 0
            last_exception = None

            while attempt < max_attempts:
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1
                    last_exception = e
                    if attempt < max_attempts:
                        wait_time = min(min_wait * (2 ** (attempt - 1)), max_wait)
                        logger.warning(
                            f"Retry {attempt}/{max_attempts} for {func.__name__} "
                            f"after {wait_time:.1f}s — {type(e).__name__}: {e}"
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__} — "
                            f"{type(e).__name__}: {e}"
                        )

            raise last_exception

        return wrapper
    return decorator


def retry_sync(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            last_exception = None

            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1
                    last_exception = e
                    if attempt < max_attempts:
                        wait_time = min(min_wait * (2 ** (attempt - 1)), max_wait)
                        logger.warning(
                            f"Retry {attempt}/{max_attempts} for {func.__name__} "
                            f"after {wait_time:.1f}s — {type(e).__name__}: {e}"
                        )
                        import time
                        time.sleep(wait_time)
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__} — "
                            f"{type(e).__name__}: {e}"
                        )

            raise last_exception

        return wrapper
    return decorator


class RetryConfig:
    EXCHANGE_ATTEMPTS = 5
    EXCHANGE_MIN_WAIT = 1.0
    EXCHANGE_MAX_WAIT = 30.0

    DB_ATTEMPTS = 3
    DB_MIN_WAIT = 0.5
    DB_MAX_WAIT = 5.0

    API_ATTEMPTS = 3
    API_MIN_WAIT = 1.0
    API_MAX_WAIT = 10.0

    TELEGRAM_ATTEMPTS = 5
    TELEGRAM_MIN_WAIT = 2.0
    TELEGRAM_MAX_WAIT = 60.0


async def safe_execute(
    func: Callable,
    *args,
    default: Any = None,
    log_error: bool = True,
    **kwargs,
) -> Any:
    try:
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        return func(*args, **kwargs)
    except Exception as e:
        if log_error:
            logger.error(f"safe_execute failed for {func.__name__}: {type(e).__name__}: {e}")
        return default


__all__ = ["retry_async", "retry_sync", "RetryConfig", "safe_execute"]

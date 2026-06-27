import asyncio
import signal
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from config.settings import settings
from utils.logger import logger
from database.connection import init_db, close_db
from scanner.market_scanner import MarketScanner
from strategy.signal_engine import SignalEngine
from bot.telegram_bot import TelegramBot
from api.router import api_router, set_scanner_refs


scanner: MarketScanner = None
signal_engine: SignalEngine = None
telegram_bot: TelegramBot = None
_tasks = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    global scanner, signal_engine, telegram_bot, _tasks

    logger.info("=" * 50)
    logger.info("  NEXARA AI — Starting Up")
    logger.info("=" * 50)

    try:
        logger.info("Initializing database...")
        await init_db()
        logger.info("Database initialized")

        logger.info("Initializing market scanner...")
        scanner = MarketScanner()
        logger.info("Market scanner initialized")

        logger.info("Initializing signal engine...")
        signal_engine = SignalEngine()
        logger.info("Signal engine initialized")

        logger.info("Initializing Telegram bot...")
        telegram_bot = TelegramBot()
        telegram_bot.set_scanner(scanner, signal_engine)
        logger.info("Telegram bot initialized")

        logger.info("Registering API scanner references...")
        set_scanner_refs(scanner, signal_engine)
        logger.info("API scanner references registered")

        async def signal_callback(data: dict) -> None:
            try:
                if data.get("type") != "scan_complete":
                    return

                results = data.get("results", [])
                if not results:
                    return

                signals = await signal_engine.process_scan_results(results)

                for sig in signals:
                    try:
                        from database.connection import AsyncSessionLocal
                        from database.crud import SignalCRUD

                        async with AsyncSessionLocal() as db:
                            is_new = await SignalCRUD.check_cooldown(
                                db,
                                sig["pair"],
                                sig["timeframe"],
                                settings.SIGNAL_COOLDOWN_MINUTES,
                            )

                        if not is_new:
                            continue

                        async with AsyncSessionLocal() as db:
                            saved = await SignalCRUD.create(db, sig)

                        if telegram_bot:
                            sent = await telegram_bot.send_signal(sig)
                            logger.info(
                                f"Signal broadcast: {sig['pair']} {sig['direction']} "
                                f"[{sig['timeframe']}] conf={sig['confidence']:.1f}% "
                                f"→ {sent} users"
                            )

                    except Exception as e:
                        logger.error(f"Error processing signal broadcast: {e}")

            except Exception as e:
                logger.error(f"Error in signal callback: {e}")

        scanner.add_signal_callback(signal_callback)

        scanner_task = asyncio.create_task(
            scanner.run_scan_loop(),
            name="scanner_loop",
        )
        _tasks.append(scanner_task)

        bot_task = asyncio.create_task(
            _run_bot(),
            name="telegram_bot",
        )
        _tasks.append(bot_task)

        logger.info("=" * 50)
        logger.info("  NEXARA AI — Fully Started")
        logger.info(f"  Environment: {settings.ENVIRONMENT}")
        logger.info(f"  API: http://{settings.API_HOST}:{settings.API_PORT}")
        logger.info(f"  Scan Interval: {settings.SCAN_INTERVAL_SECONDS}s")
        logger.info(f"  Min Confidence: {settings.MIN_CONFIDENCE_SCORE}%")
        logger.info("=" * 50)

        yield

    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise
    finally:
        logger.info("NEXARA AI — Shutting down...")

        for task in _tasks:
            if not task.done():
                task.cancel()
                try:
                    await asyncio.wait_for(task, timeout=5.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass

        if scanner:
            await scanner.close()

        if telegram_bot:
            await telegram_bot.stop()

        await close_db()

        logger.info("NEXARA AI — Shutdown complete")


async def _run_bot():
    try:
        if telegram_bot:
            await telegram_bot.start()
    except Exception as e:
        logger.error(f"Bot error: {e}")


limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="NEXARA AI",
    description="Institutional-grade AI crypto trading platform",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"],
)

app.include_router(api_router)


def handle_shutdown(signum, frame):
    logger.info(f"Received signal {signum}. Initiating shutdown...")
    sys.exit(0)


signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        workers=settings.API_WORKERS,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=settings.DEBUG,
    )

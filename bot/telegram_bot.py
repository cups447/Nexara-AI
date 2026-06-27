import asyncio
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeDefault

from config.settings import settings
from utils.logger import logger
from database.connection import init_db
from bot.handlers import (
    start_router,
    signals_router,
    scan_router,
    watchlist_router,
    settings_router,
    info_router,
)
from bot.handlers.signals import broadcast_signal
from bot.handlers.scan import set_scanner as scan_set_scanner
from bot.handlers.watchlist import set_scanner as watchlist_set_scanner
from bot.handlers.info import set_scanner as info_set_scanner


class TelegramBot:

    def __init__(self):
        self.bot = Bot(
            token=settings.TELEGRAM_BOT_TOKEN,
            default=DefaultBotProperties(
                parse_mode=ParseMode.HTML,
            ),
        )
        self.storage = MemoryStorage()
        self.dp = Dispatcher(storage=self.storage)
        self._scanner = None
        self._signal_engine = None
        self._running = False

    def set_scanner(self, scanner, signal_engine) -> None:
        self._scanner = scanner
        self._signal_engine = signal_engine
        scan_set_scanner(scanner, signal_engine)
        watchlist_set_scanner(scanner, signal_engine)
        info_set_scanner(scanner)
        logger.info("Scanner and signal engine connected to bot handlers")

    def _register_routers(self) -> None:
        self.dp.include_router(start_router)
        self.dp.include_router(signals_router)
        self.dp.include_router(scan_router)
        self.dp.include_router(watchlist_router)
        self.dp.include_router(settings_router)
        self.dp.include_router(info_router)
        logger.info("All routers registered")

    async def _set_commands(self) -> None:
        try:
            commands = [
                BotCommand(command="start", description="🚀 Start NEXARA AI"),
                BotCommand(command="help", description="📚 Help & Commands"),
                BotCommand(command="signals", description="📊 View AI Signals"),
                BotCommand(command="top", description="🔥 Top 10 Signals"),
                BotCommand(command="scan", description="🔍 Scan Markets"),
                BotCommand(command="watchlist", description="👀 Manage Watchlist"),
                BotCommand(command="status", description="📡 System Status"),
                BotCommand(command="settings", description="⚙️ Settings"),
                BotCommand(command="news", description="📰 Crypto News"),
                BotCommand(command="fear", description="😱 Fear & Greed Index"),
            ]
            await self.bot.set_my_commands(
                commands,
                scope=BotCommandScopeDefault(),
            )
            logger.info("Bot commands set successfully")
        except Exception as e:
            logger.error(f"Error setting bot commands: {e}")

    async def _notify_admins(self, message: str) -> None:
        for admin_id in settings.TELEGRAM_ADMIN_IDS:
            try:
                await self.bot.send_message(
                    chat_id=admin_id,
                    text=message,
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.error(f"Error notifying admin {admin_id}: {e}")

    async def send_signal(self, signal: dict) -> int:
        try:
            sent = await broadcast_signal(self.bot, signal)
            return sent
        except Exception as e:
            logger.error(f"Error sending signal: {e}")
            return 0

    async def send_message_to_user(
        self,
        telegram_id: int,
        text: str,
        parse_mode: str = "HTML",
    ) -> bool:
        try:
            await self.bot.send_message(
                chat_id=telegram_id,
                text=text,
                parse_mode=parse_mode,
                disable_web_page_preview=True,
            )
            return True
        except Exception as e:
            logger.error(f"Error sending message to {telegram_id}: {e}")
            return False

    async def send_to_channel(
        self,
        text: str,
        parse_mode: str = "HTML",
    ) -> bool:
        try:
            if not settings.TELEGRAM_CHANNEL_ID:
                return False
            await self.bot.send_message(
                chat_id=settings.TELEGRAM_CHANNEL_ID,
                text=text,
                parse_mode=parse_mode,
                disable_web_page_preview=True,
            )
            return True
        except Exception as e:
            logger.error(f"Error sending to channel: {e}")
            return False

    async def start(self) -> None:
        try:
            logger.info("Initializing database...")
            await init_db()

            logger.info("Registering routers...")
            self._register_routers()

            logger.info("Setting bot commands...")
            await self._set_commands()

            bot_info = await self.bot.get_me()
            logger.info(
                f"Bot started: @{bot_info.username} (ID: {bot_info.id})"
            )

            await self._notify_admins(
                f"🚀 <b>NEXARA AI Started!</b>\n\n"
                f"Bot: @{bot_info.username}\n"
                f"Environment: {settings.ENVIRONMENT}\n"
                f"Version: 1.0.0\n\n"
                f"⚡ <i>NEXARA AI is online</i>"
            )

            self._running = True
            logger.info("Starting bot polling...")

            await self.dp.start_polling(
                self.bot,
                allowed_updates=self.dp.resolve_used_update_types(),
                drop_pending_updates=True,
            )
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            raise

    async def stop(self) -> None:
        try:
            self._running = False

            await self._notify_admins(
                "🔴 <b>NEXARA AI Stopped!</b>\n\n"
                "The bot has been shut down.\n\n"
                "⚡ <i>NEXARA AI</i>"
            )

            await self.dp.stop_polling()
            await self.bot.session.close()
            logger.info("Bot stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")

    async def run_with_scanner(
        self,
        scanner,
        signal_engine,
    ) -> None:
        try:
            self.set_scanner(scanner, signal_engine)

            async def signal_callback(data: dict) -> None:
                try:
                    if data.get("type") != "scan_complete":
                        return

                    results = data.get("results", [])
                    if not results:
                        return

                    signals = await signal_engine.process_scan_results(results)

                    for signal in signals:
                        try:
                            from database.connection import AsyncSessionLocal
                            from database.crud import SignalCRUD

                            async with AsyncSessionLocal() as db:
                                is_new = await SignalCRUD.check_cooldown(
                                    db,
                                    signal["pair"],
                                    signal["timeframe"],
                                    settings.SIGNAL_COOLDOWN_MINUTES,
                                )

                            if not is_new:
                                continue

                            async with AsyncSessionLocal() as db:
                                saved = await SignalCRUD.create(db, signal)

                            sent = await self.send_signal(signal)
                            logger.info(
                                f"Signal sent: {signal['pair']} {signal['direction']} "
                                f"conf={signal['confidence']:.1f}% → {sent} users"
                            )
                        except Exception as e:
                            logger.error(f"Error processing signal for broadcast: {e}")

                except Exception as e:
                    logger.error(f"Error in signal callback: {e}")

            scanner.add_signal_callback(signal_callback)

            bot_task = asyncio.create_task(self.start())
            scanner_task = asyncio.create_task(
                scanner.run_scan_loop()
            )

            logger.info("NEXARA AI fully started — Bot + Scanner running")

            done, pending = await asyncio.wait(
                [bot_task, scanner_task],
                return_when=asyncio.FIRST_EXCEPTION,
            )

            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

            for task in done:
                if task.exception():
                    raise task.exception()

        except Exception as e:
            logger.error(f"Error in run_with_scanner: {e}")
            raise


__all__ = ["TelegramBot"]

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

from config.settings import settings
from database.connection import AsyncSessionLocal
from database.crud import UserCRUD, PremiumCRUD, SettingCRUD
from bot.keyboards.menus import BotKeyboards
from utils.logger import logger

router = Router()


async def get_or_create_user(message: Message):
    try:
        async with AsyncSessionLocal() as db:
            user, created = await UserCRUD.get_or_create(
                db=db,
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
                language_code=message.from_user.language_code or "en",
            )
            return user, created
    except Exception as e:
        logger.error(f"Error getting/creating user: {e}")
        return None, False


@router.message(CommandStart())
async def handle_start(message: Message, state: FSMContext):
    try:
        await state.clear()
        user, created = await get_or_create_user(message)
        first_name = message.from_user.first_name or "Trader"

        if created:
            welcome_text = (
                f"🚀 <b>Welcome to NEXARA AI!</b>\n\n"
                f"Hello <b>{first_name}</b>! 👋\n\n"
                f"You've just joined the most advanced institutional-grade crypto trading platform.\n\n"
                f"<b>What NEXARA AI offers:</b>\n"
                f"• 🎯 AI-powered signals with 90%+ confidence\n"
                f"• 📊 19+ technical indicators analyzed\n"
                f"• 💎 Smart Money Concepts (SMC) detection\n"
                f"• ⚡ Real-time market scanning every 30 seconds\n"
                f"• 🛡️ Institutional-grade risk management\n"
                f"• 📈 All Binance USDT Futures pairs covered\n\n"
                f"<b>Use the menu below to get started!</b>\n\n"
                f"⚡ <i>Powered by NEXARA AI</i>"
            )
        else:
            welcome_text = (
                f"🚀 <b>Welcome back, {first_name}!</b>\n\n"
                f"NEXARA AI is scanning the markets for you.\n\n"
                f"Use the menu below to access signals, scans, and more.\n\n"
                f"⚡ <i>Powered by NEXARA AI</i>"
            )

        await message.answer(
            welcome_text,
            reply_markup=BotKeyboards.main_menu(),
            parse_mode="HTML",
        )

        logger.info(
            f"User {'registered' if created else 'returned'}: "
            f"{message.from_user.id} (@{message.from_user.username})"
        )
    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        await message.answer(
            "❌ An error occurred. Please try again.",
            reply_markup=BotKeyboards.main_menu(),
        )


@router.message(Command("help"))
async def handle_help(message: Message):
    try:
        help_text = (
            "📚 <b>NEXARA AI — Command Guide</b>\n\n"
            "<b>📊 Trading Commands:</b>\n"
            "/signals — View latest AI signals\n"
            "/top — Top 10 highest confidence signals\n"
            "/scan — Trigger market scan\n"
            "/watchlist — Manage your watchlist\n\n"
            "<b>ℹ️ Info Commands:</b>\n"
            "/status — Scanner & system status\n"
            "/news — Latest crypto news\n"
            "/fear — Fear & Greed Index\n\n"
            "<b>⚙️ User Commands:</b>\n"
            "/settings — Configure your preferences\n"
            "/start — Return to main menu\n"
            "/help — Show this help message\n\n"
            "<b>📈 Signal Format:</b>\n"
            "• Entry, SL, TP1, TP2, TP3\n"
            "• Risk/Reward ratio\n"
            "• AI Confidence score\n"
            "• SMC confirmations\n"
            "• Estimated win rate\n\n"
            "<b>🎯 Signal Quality:</b>\n"
            "• Only signals with 90%+ confidence\n"
            "• Multiple timeframe confirmation\n"
            "• SMC + Technical confluence\n\n"
            "⚡ <i>NEXARA AI — Trade with Intelligence</i>"
        )

        await message.answer(
            help_text,
            reply_markup=BotKeyboards.main_menu(),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Error in help handler: {e}")
        await message.answer("❌ An error occurred. Please try again.")


@router.callback_query(F.data == "main_menu")
async def handle_main_menu_callback(callback: CallbackQuery, state: FSMContext):
    try:
        await state.clear()
        first_name = callback.from_user.first_name or "Trader"

        await callback.message.edit_text(
            f"🚀 <b>NEXARA AI — Main Menu</b>\n\n"
            f"Hello <b>{first_name}</b>! Use the menu below.\n\n"
            f"⚡ <i>Powered by NEXARA AI</i>",
            parse_mode="HTML",
        )

        await callback.message.answer(
            "Choose an option:",
            reply_markup=BotKeyboards.main_menu(),
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in main menu callback: {e}")
        await callback.answer("❌ Error occurred", show_alert=True)


@router.callback_query(F.data == "cancel_action")
async def handle_cancel(callback: CallbackQuery, state: FSMContext):
    try:
        await state.clear()
        await callback.message.edit_text(
            "❌ <b>Action cancelled.</b>",
            parse_mode="HTML",
        )
        await callback.answer("Cancelled")
    except Exception as e:
        logger.error(f"Error in cancel handler: {e}")
        await callback.answer("❌ Error occurred")


@router.callback_query(F.data == "noop")
async def handle_noop(callback: CallbackQuery):
    try:
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in noop handler: {e}")


@router.message(F.text == "📊 Signals")
async def handle_signals_button(message: Message):
    try:
        from bot.handlers.signals import handle_signals
        await handle_signals(message)
    except Exception as e:
        logger.error(f"Error routing to signals: {e}")
        await message.answer("❌ Error occurred. Please use /signals")


@router.message(F.text == "🔥 Top Signals")
async def handle_top_signals_button(message: Message):
    try:
        from bot.handlers.signals import handle_top
        await handle_top(message)
    except Exception as e:
        logger.error(f"Error routing to top signals: {e}")
        await message.answer("❌ Error occurred. Please use /top")


@router.message(F.text == "🔍 Scan")
async def handle_scan_button(message: Message):
    try:
        from bot.handlers.scan import handle_scan
        await handle_scan(message)
    except Exception as e:
        logger.error(f"Error routing to scan: {e}")
        await message.answer("❌ Error occurred. Please use /scan")


@router.message(F.text == "👀 Watchlist")
async def handle_watchlist_button(message: Message):
    try:
        from bot.handlers.watchlist import handle_watchlist
        await handle_watchlist(message)
    except Exception as e:
        logger.error(f"Error routing to watchlist: {e}")
        await message.answer("❌ Error occurred. Please use /watchlist")


@router.message(F.text == "📰 News")
async def handle_news_button(message: Message):
    try:
        from bot.handlers.info import handle_news
        await handle_news(message)
    except Exception as e:
        logger.error(f"Error routing to news: {e}")
        await message.answer("❌ Error occurred. Please use /news")


@router.message(F.text == "😱 Fear & Greed")
async def handle_fear_button(message: Message):
    try:
        from bot.handlers.info import handle_fear
        await handle_fear(message)
    except Exception as e:
        logger.error(f"Error routing to fear greed: {e}")
        await message.answer("❌ Error occurred. Please use /fear")


@router.message(F.text == "⚙️ Settings")
async def handle_settings_button(message: Message):
    try:
        from bot.handlers.settings import handle_settings
        await handle_settings(message)
    except Exception as e:
        logger.error(f"Error routing to settings: {e}")
        await message.answer("❌ Error occurred. Please use /settings")


@router.message(F.text == "📡 Status")
async def handle_status_button(message: Message):
    try:
        from bot.handlers.info import handle_status
        await handle_status(message)
    except Exception as e:
        logger.error(f"Error routing to status: {e}")
        await message.answer("❌ Error occurred. Please use /status")


__all__ = ["router"]

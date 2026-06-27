import asyncio
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from config.settings import settings
from database.connection import AsyncSessionLocal
from database.crud import SignalCRUD, UserCRUD, SettingCRUD
from bot.keyboards.menus import BotKeyboards
from utils.logger import logger
from utils.formatters import SignalFormatter

router = Router()

_scanner_ref = None
_signal_engine_ref = None


def set_scanner(scanner, signal_engine):
    global _scanner_ref, _signal_engine_ref
    _scanner_ref = scanner
    _signal_engine_ref = signal_engine


@router.message(Command("scan"))
async def handle_scan(message: Message):
    try:
        await message.answer(
            "🔍 <b>NEXARA AI — Market Scanner</b>\n\n"
            "Choose a scan option:",
            reply_markup=BotKeyboards.scan_menu(),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Error in scan handler: {e}")
        await message.answer("❌ Error opening scan menu.")


@router.callback_query(F.data == "scan_menu")
async def handle_scan_menu_callback(callback: CallbackQuery):
    try:
        await callback.message.edit_text(
            "🔍 <b>NEXARA AI — Market Scanner</b>\n\n"
            "Choose a scan option:",
            reply_markup=BotKeyboards.scan_menu(),
            parse_mode="HTML",
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in scan menu callback: {e}")
        await callback.answer("❌ Error", show_alert=True)


@router.callback_query(F.data == "scan_status")
async def handle_scan_status_callback(callback: CallbackQuery):
    try:
        await callback.answer("Loading status...")

        if _scanner_ref is None:
            await callback.message.edit_text(
                "⚠️ <b>Scanner not initialized yet.</b>\n\n"
                "Please wait for the system to start.\n\n"
                "⚡ <i>NEXARA AI</i>",
                parse_mode="HTML",
                reply_markup=BotKeyboards.scan_menu(),
            )
            return

        status = _scanner_ref.get_status()
        text = SignalFormatter.format_scan_status(status)

        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=BotKeyboards.scan_menu(),
        )
    except Exception as e:
        logger.error(f"Error in scan status callback: {e}")
        await callback.answer("❌ Error loading status", show_alert=True)


@router.callback_query(F.data == "scan_quick")
async def handle_quick_scan_callback(callback: CallbackQuery):
    try:
        await callback.answer("Starting quick scan...")

        if _scanner_ref is None or _signal_engine_ref is None:
            await callback.message.edit_text(
                "⚠️ <b>Scanner not available yet.</b>\n\n"
                "Please wait for the system to initialize.\n\n"
                "⚡ <i>NEXARA AI</i>",
                parse_mode="HTML",
                reply_markup=BotKeyboards.scan_menu(),
            )
            return

        loading_msg = await callback.message.edit_text(
            "⏳ <b>Running quick scan...</b>\n\n"
            "Scanning top 20 pairs on 15m & 1H timeframes.\n"
            "This may take 30-60 seconds.\n\n"
            "⚡ <i>NEXARA AI</i>",
            parse_mode="HTML",
        )

        pairs = await _scanner_ref.pair_filter.get_filtered_pairs(max_pairs=20)
        results = await _scanner_ref.scan_all_pairs(
            pairs=pairs,
            timeframes=["15m", "1h"],
        )

        signals = await _signal_engine_ref.process_scan_results(results)

        if not signals:
            await loading_msg.edit_text(
                "✅ <b>Quick scan complete!</b>\n\n"
                "⚠️ No high-confidence signals found.\n\n"
                f"📊 Pairs scanned: <code>{len(pairs)}</code>\n"
                f"📈 Results analyzed: <code>{len(results)}</code>\n\n"
                "The market conditions don't meet our 90%+ confidence threshold.\n"
                "Check back in a few minutes!\n\n"
                "⚡ <i>NEXARA AI</i>",
                parse_mode="HTML",
                reply_markup=BotKeyboards.scan_menu(),
            )
            return

        await loading_msg.edit_text(
            f"✅ <b>Quick scan complete!</b>\n\n"
            f"🎯 Found <b>{len(signals)}</b> high-confidence signal(s)!\n\n"
            f"📊 Pairs scanned: <code>{len(pairs)}</code>\n"
            f"📈 Results analyzed: <code>{len(results)}</code>\n\n"
            f"⚡ <i>NEXARA AI</i>",
            parse_mode="HTML",
            reply_markup=BotKeyboards.scan_menu(),
        )

        for signal in signals[:3]:
            async with AsyncSessionLocal() as db:
                is_new = await SignalCRUD.check_cooldown(
                    db,
                    signal["pair"],
                    signal["timeframe"],
                )

            if is_new:
                async with AsyncSessionLocal() as db:
                    saved = await SignalCRUD.create(db, signal)

                text = SignalFormatter.format_signal(signal)
                await callback.message.answer(
                    text,
                    parse_mode="HTML",
                    reply_markup=BotKeyboards.signal_detail(saved.id),
                    disable_web_page_preview=True,
                )
                await asyncio.sleep(0.5)

    except Exception as e:
        logger.error(f"Error in quick scan callback: {e}")
        await callback.answer("❌ Error running scan", show_alert=True)


@router.callback_query(F.data == "scan_all")
async def handle_scan_all_callback(callback: CallbackQuery):
    try:
        await callback.answer("Starting full scan...")

        if _scanner_ref is None or _signal_engine_ref is None:
            await callback.message.edit_text(
                "⚠️ <b>Scanner not available yet.</b>\n\n"
                "⚡ <i>NEXARA AI</i>",
                parse_mode="HTML",
                reply_markup=BotKeyboards.scan_menu(),
            )
            return

        loading_msg = await callback.message.edit_text(
            "⏳ <b>Running full market scan...</b>\n\n"
            "Scanning ALL Binance USDT Futures pairs.\n"
            "This may take 2-5 minutes.\n\n"
            "Results will be sent automatically.\n\n"
            "⚡ <i>NEXARA AI</i>",
            parse_mode="HTML",
        )

        asyncio.create_task(
            _run_full_scan_and_notify(
                callback.message,
                callback.from_user.id,
            )
        )

        await loading_msg.edit_text(
            "✅ <b>Full scan started in background!</b>\n\n"
            "You will receive signals as they are discovered.\n\n"
            "⚡ <i>NEXARA AI</i>",
            parse_mode="HTML",
            reply_markup=BotKeyboards.scan_menu(),
        )

    except Exception as e:
        logger.error(f"Error in full scan callback: {e}")
        await callback.answer("❌ Error starting scan", show_alert=True)


async def _run_full_scan_and_notify(message, user_telegram_id: int):
    try:
        pairs = await _scanner_ref.pair_filter.get_filtered_pairs()
        results = await _scanner_ref.scan_all_pairs(pairs=pairs)
        signals = await _signal_engine_ref.process_scan_results(results)

        if not signals:
            await message.answer(
                "✅ <b>Full scan complete!</b>\n\n"
                f"📊 Pairs scanned: <code>{len(pairs)}</code>\n"
                "⚠️ No high-confidence signals found.\n\n"
                "⚡ <i>NEXARA AI</i>",
                parse_mode="HTML",
                reply_markup=BotKeyboards.scan_menu(),
            )
            return

        await message.answer(
            f"✅ <b>Full scan complete!</b>\n\n"
            f"🎯 Found <b>{len(signals)}</b> signal(s)!\n"
            f"📊 Pairs scanned: <code>{len(pairs)}</code>\n\n"
            f"⚡ <i>NEXARA AI</i>",
            parse_mode="HTML",
        )

        for signal in signals[:5]:
            async with AsyncSessionLocal() as db:
                is_new = await SignalCRUD.check_cooldown(
                    db,
                    signal["pair"],
                    signal["timeframe"],
                )

            if is_new:
                async with AsyncSessionLocal() as db:
                    saved = await SignalCRUD.create(db, signal)

                text = SignalFormatter.format_signal(signal)
                await message.answer(
                    text,
                    parse_mode="HTML",
                    reply_markup=BotKeyboards.signal_detail(saved.id),
                    disable_web_page_preview=True,
                )
                await asyncio.sleep(1.0)

    except Exception as e:
        logger.error(f"Error in background full scan: {e}")
        try:
            await message.answer(
                "❌ <b>Scan encountered an error.</b>\n\n"
                "Please try again later.\n\n"
                "⚡ <i>NEXARA AI</i>",
                parse_mode="HTML",
                reply_markup=BotKeyboards.scan_menu(),
            )
        except Exception:
            pass


@router.callback_query(F.data.startswith("scan_tf_"))
async def handle_scan_timeframe_callback(callback: CallbackQuery):
    try:
        timeframe = callback.data.replace("scan_tf_", "")
        await callback.answer(f"Scanning {timeframe}...")

        if _scanner_ref is None or _signal_engine_ref is None:
            await callback.answer("❌ Scanner not available", show_alert=True)
            return

        loading_msg = await callback.message.edit_text(
            f"⏳ <b>Scanning {timeframe} timeframe...</b>\n\n"
            f"Analyzing top pairs on {timeframe}.\n\n"
            "⚡ <i>NEXARA AI</i>",
            parse_mode="HTML",
        )

        pairs = await _scanner_ref.pair_filter.get_filtered_pairs(max_pairs=50)
        results = await _scanner_ref.scan_all_pairs(
            pairs=pairs,
            timeframes=[timeframe],
        )
        signals = await _signal_engine_ref.process_scan_results(results)

        if not signals:
            await loading_msg

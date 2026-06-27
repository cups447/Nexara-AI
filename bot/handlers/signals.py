from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from typing import List, Optional

from config.settings import settings
from database.connection import AsyncSessionLocal
from database.crud import SignalCRUD, UserCRUD, SettingCRUD
from bot.keyboards.menus import BotKeyboards
from utils.logger import logger
from utils.formatters import SignalFormatter

router = Router()


async def _get_user_min_confidence(telegram_id: int) -> float:
    try:
        async with AsyncSessionLocal() as db:
            user = await UserCRUD.get_by_telegram_id(db, telegram_id)
            if not user:
                return settings.MIN_CONFIDENCE_SCORE
            setting = await SettingCRUD.get_by_user_id(db, user.id)
            if not setting:
                return settings.MIN_CONFIDENCE_SCORE
            return setting.min_confidence
    except Exception as e:
        logger.error(f"Error getting user min confidence: {e}")
        return settings.MIN_CONFIDENCE_SCORE


@router.message(Command("signals"))
@router.message(F.text == "📊 Signals")
async def handle_signals(message: Message):
    try:
        await message.answer(
            "📊 <b>NEXARA AI Signals</b>\n\nChoose signal type:",
            reply_markup=BotKeyboards.signals_menu(),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Error in signals handler: {e}")
        await message.answer("❌ Error loading signals menu.")


@router.message(Command("top"))
async def handle_top(message: Message):
    try:
        loading_msg = await message.answer(
            "⏳ <b>Loading top signals...</b>",
            parse_mode="HTML",
        )

        min_confidence = await _get_user_min_confidence(message.from_user.id)

        async with AsyncSessionLocal() as db:
            signals = await SignalCRUD.get_top(db, limit=10, hours=24)

        if not signals:
            await loading_msg.edit_text(
                "⚠️ <b>No top signals found in the last 24 hours.</b>\n\n"
                "The scanner is analyzing markets. Check back soon!\n\n"
                "⚡ <i>NEXARA AI</i>",
                parse_mode="HTML",
                reply_markup=BotKeyboards.refresh_button("signals_top"),
            )
            return

        signal_dicts = [s.to_dict() for s in signals]
        text = SignalFormatter.format_top_signals(signal_dicts)

        await loading_msg.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=BotKeyboards.signals_menu(),
            disable_web_page_preview=True,
        )
    except Exception as e:
        logger.error(f"Error in top signals handler: {e}")
        await message.answer("❌ Error loading top signals.")


@router.callback_query(F.data == "signals_top")
async def handle_signals_top_callback(callback: CallbackQuery):
    try:
        await callback.answer("Loading top signals...")

        async with AsyncSessionLocal() as db:
            signals = await SignalCRUD.get_top(db, limit=10, hours=24)

        if not signals:
            await callback.message.edit_text(
                "⚠️ <b>No top signals found in the last 24 hours.</b>\n\n"
                "⚡ <i>NEXARA AI</i>",
                parse_mode="HTML",
                reply_markup=BotKeyboards.signals_menu(),
            )
            return

        signal_dicts = [s.to_dict() for s in signals]
        text = SignalFormatter.format_top_signals(signal_dicts)

        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=BotKeyboards.signals_menu(),
            disable_web_page_preview=True,
        )
    except Exception as e:
        logger.error(f"Error in top signals callback: {e}")
        await callback.answer("❌ Error loading signals", show_alert=True)


@router.callback_query(F.data == "signals_active")
async def handle_signals_active_callback(callback: CallbackQuery):
    try:
        await callback.answer("Loading active signals...")

        min_confidence = await _get_user_min_confidence(callback.from_user.id)

        async with AsyncSessionLocal() as db:
            signals = await SignalCRUD.get_recent(
                db,
                limit=5,
                min_confidence=min_confidence,
            )

        if not signals:
            await callback.message.edit_text(
                "⚠️ <b>No active signals right now.</b>\n\n"
                "The AI is scanning markets every 30 seconds.\n"
                "High-confidence signals will appear here.\n\n"
                "⚡ <i>NEXARA AI</i>",
                parse_mode="HTML",
                reply_markup=BotKeyboards.signals_menu(),
            )
            return

        text_parts = []
        for signal in signals:
            text_parts.append(SignalFormatter.format_signal(signal.to_dict()))
            text_parts.append("\n" + "─" * 32 + "\n")

        full_text = "\n".join(text_parts)

        if len(full_text) > 4096:
            for signal in signals[:2]:
                await callback.message.answer(
                    SignalFormatter.format_signal(signal.to_dict()),
                    parse_mode="HTML",
                    reply_markup=BotKeyboards.signal_detail(signal.id),
                )
            await callback.message.edit_text(
                f"📊 Showing {min(2, len(signals))} of {len(signals)} active signals.",
                parse_mode="HTML",
                reply_markup=BotKeyboards.signals_menu(),
            )
        else:
            await callback.message.edit_text(
                full_text,
                parse_mode="HTML",
                reply_markup=BotKeyboards.signals_menu(),
                disable_web_page_preview=True,
            )
    except Exception as e:
        logger.error(f"Error in active signals callback: {e}")
        await callback.answer("❌ Error loading signals", show_alert=True)


@router.callback_query(F.data == "signals_long")
async def handle_signals_long_callback(callback: CallbackQuery):
    try:
        await callback.answer("Loading LONG signals...")

        min_confidence = await _get_user_min_confidence(callback.from_user.id)

        async with AsyncSessionLocal() as db:
            all_signals = await SignalCRUD.get_recent(
                db,
                limit=20,
                min_confidence=min_confidence,
            )

        long_signals = [s for s in all_signals if s.direction == "LONG"]

        if not long_signals:
            await callback.message.edit_text(
                "⚠️ <b>No active LONG signals right now.</b>\n\n"
                "⚡ <i>NEXARA AI</i>",
                parse_mode="HTML",
                reply_markup=BotKeyboards.signals_menu(),
            )
            return

        signal_dicts = [s.to_dict() for s in long_signals[:5]]
        text = SignalFormatter.format_top_signals(signal_dicts)

        await callback.message.edit_text(
            f"🟢 <b>LONG Signals</b>\n\n{text}",
            parse_mode="HTML",
            reply_markup=BotKeyboards.signals_menu(),
            disable_web_page_preview=True,
        )
    except Exception as e:
        logger.error(f"Error in long signals callback: {e}")
        await callback.answer("❌ Error loading signals", show_alert=True)


@router.callback_query(F.data == "signals_short")
async def handle_signals_short_callback(callback: CallbackQuery):
    try:
        await callback.answer("Loading SHORT signals...")

        min_confidence = await _get_user_min_confidence(callback.from_user.id)

        async with AsyncSessionLocal() as db:
            all_signals = await SignalCRUD.get_recent(
                db,
                limit=20,
                min_confidence=min_confidence,
            )

        short_signals = [s for s in all_signals if s.direction == "SHORT"]

        if not short_signals:
            await callback.message.edit_text(
                "⚠️ <b>No active SHORT signals right now.</b>\n\n"
                "⚡ <i>NEXARA AI</i>",
                parse_mode="HTML",
                reply_markup=BotKeyboards.signals_menu(),
            )
            return

        signal_dicts = [s.to_dict() for s in short_signals[:5]]
        text = SignalFormatter.format_top_signals(signal_dicts)

        await callback.message.edit_text(
            f"🔴 <b>SHORT Signals</b>\n\n{text}",
            parse_mode="HTML",
            reply_markup=BotKeyboards.signals_menu(),
            disable_web_page_preview=True,
        )
    except Exception as e:
        logger.error(f"Error in short signals callback: {e}")
        await callback.answer("❌ Error loading signals", show_alert=True)


@router.callback_query(F.data.startswith("signals_tf_"))
async def handle_signals_timeframe_callback(callback: CallbackQuery):
    try:
        timeframe = callback.data.replace("signals_tf_", "")
        await callback.answer(f"Loading {timeframe} signals...")

        min_confidence = await _get_user_min_confidence(callback.from_user.id)

        async with AsyncSessionLocal() as db:
            all_signals = await SignalCRUD.get_recent(
                db,
                limit=20,
                min_confidence=min_confidence,
            )

        tf_signals = [s for s in all_signals if s.timeframe == timeframe]

        if not tf_signals:
            await callback.message.edit_text(
                f"⚠️ <b>No active {timeframe} signals right now.</b>\n\n"
                f"⚡ <i>NEXARA AI</i>",
                parse_mode="HTML",
                reply_markup=BotKeyboards.signals_menu(),
            )
            return

        signal_dicts = [s.to_dict() for s in tf_signals[:5]]
        text = SignalFormatter.format_top_signals(signal_dicts)

        await callback.message.edit_text(
            f"⏱️ <b>{timeframe} Signals</b>\n\n{text}",
            parse_mode="HTML",
            reply_markup=BotKeyboards.signals_menu(),
            disable_web_page_preview=True,
        )
    except Exception as e:
        logger.error(f"Error in timeframe signals callback: {e}")
        await callback.answer("❌ Error loading signals", show_alert=True)


@router.callback_query(F.data == "signals_refresh")
async def handle_signals_refresh_callback(callback: CallbackQuery):
    try:
        await callback.answer("Refreshing signals...")
        await handle_signals_active_callback(callback)
    except Exception as e:
        logger.error(f"Error in signals refresh callback: {e}")
        await callback.answer("❌ Error refreshing", show_alert=True)


@router.callback_query(F.data.startswith("signal_analysis_"))
async def handle_signal_analysis_callback(callback: CallbackQuery):
    try:
        signal_id = int(callback.data.replace("signal_analysis_", ""))
        await callback.answer("Loading analysis...")

        async with AsyncSessionLocal() as db:
            signal = await SignalCRUD.get_by_id(db, signal_id)

        if not signal:
            await callback.answer("❌ Signal not found", show_alert=True)
            return

        signal_dict = signal.to_dict()
        ai_scores = signal_dict.get("ai_scores", {})
        component_scores = signal_dict.get("component_confluence", {})

        analysis_text = (
            f"📊 <b>FULL SIGNAL ANALYSIS</b>\n"
            f"{'─' * 32}\n"
            f"<b>Pair:</b> <code>{signal.pair}</code> [{signal.timeframe}]\n"
            f"<b>Direction:</b> {'🟢 LONG' if signal.direction == 'LONG' else '🔴 SHORT'}\n"
            f"<b>Confidence:</b> <code>{signal.confidence:.1f}%</code>\n\n"
            f"<b>🤖 AI Component Scores:</b>\n"
        )

        if ai_scores:
            for key, val in ai_scores.items():
                bar = "█" * int(val / 10) + "░" * (10 - int(val / 10))
                analysis_text += f"  {key.title()}: [{bar}] {val:.0f}\n"
        else:
            analysis_text += "  Score breakdown not available\n"

        analysis_text += (
            f"\n<b>📈 Confluence Breakdown:</b>\n"
        )

        if component_scores:
            for key, val in component_scores.items():
                direction_emoji = "🟢" if val > 0 else "🔴" if val < 0 else "⚪"
                analysis_text += f"  {direction_emoji} {key.title()}: {val:+.2f}\n"
        else:
            analysis_text += "  Breakdown not available\n"

        analysis_text += f"\n<i>⚡ NEXARA AI | Signal #{signal.id}</i>"

        await callback.message.edit_text(
            analysis_text,
            parse_mode="HTML",
            reply_markup=BotKeyboards.signal_detail(signal_id),
        )
    except Exception as e:
        logger.error(f"Error in signal analysis callback: {e}")
        await callback.answer("❌ Error loading analysis", show_alert=True)


@router.callback_query(F.data.startswith("signal_refresh_"))
async def handle_signal_refresh_callback(callback: CallbackQuery):
    try:
        signal_id = int(callback.data.replace("signal_refresh_", ""))
        await callback.answer("Refreshing signal...")

        async with AsyncSessionLocal() as db:
            signal = await SignalCRUD.get_by_id(db, signal_id)

        if not signal:
            await callback.answer("❌ Signal not found", show_alert=True)
            return

        text = SignalFormatter.format_signal(signal.to_dict())

        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=BotKeyboards.signal_detail(signal_id),
            disable_web_page_preview=True,
        )
    except Exception as e:
        logger.error(f"Error refreshing signal: {e}")
        await callback.answer("❌ Error refreshing signal", show_alert=True)


async def broadcast_signal(
    bot,
    signal_dict: dict,
    db_session=None,
) -> int:
    try:
        text = SignalFormatter.format_signal(signal_dict)
        sent_count = 0

        async with AsyncSessionLocal() as db:
            users = await UserCRUD.get_all_active(db)

        for user in users:
            try:
                if not user.is_active or user.is_banned:
                    continue

                async with AsyncSessionLocal() as db:
                    setting = await SettingCRUD.get_by_user_id(db, user.id)

                if setting and not setting.signal_notifications:
                    continue

                if setting and signal_dict.get("confidence", 0) < setting.min_confidence:
                    continue

                if setting and signal_dict.get("timeframe") not in setting.get_preferred_timeframes():
                    continue

                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=text,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )

                async with AsyncSessionLocal() as db:
                    await UserCRUD.increment_signals(db, user.telegram_id)

                sent_count += 1

                import asyncio
                await asyncio.sleep(0.05)

            except Exception as e:
                logger.error(f"Error sending signal to user {user.telegram_id}: {e}")
                continue

        if settings.TELEGRAM_CHANNEL_ID:
            try:
                await bot.send_message(
                    chat_id=settings.TELEGRAM_CHANNEL_ID,
                    text=text,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
            except Exception as e:
                logger.error(f"Error sending to channel: {e}")

        logger.info(f"Signal broadcast complete: sent to {sent_count} users")
        return sent_count
    except Exception as e:
        logger.error(f"Error broadcasting signal: {e}")
        return 0


__all__ = ["router", "broadcast_signal"]

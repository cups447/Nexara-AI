import json
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config.settings import settings
from database.connection import AsyncSessionLocal
from database.crud import UserCRUD, SettingCRUD
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


class WatchlistStates(StatesGroup):
    waiting_for_pair = State()
    waiting_for_remove = State()


async def _get_user_watchlist(telegram_id: int) -> list:
    try:
        async with AsyncSessionLocal() as db:
            user = await UserCRUD.get_by_telegram_id(db, telegram_id)
            if not user:
                return []
            setting = await SettingCRUD.get_by_user_id(db, user.id)
            if not setting:
                return []
            return setting.get_preferred_pairs()
    except Exception as e:
        logger.error(f"Error getting watchlist for {telegram_id}: {e}")
        return []


async def _save_user_watchlist(telegram_id: int, pairs: list) -> bool:
    try:
        async with AsyncSessionLocal() as db:
            user = await UserCRUD.get_by_telegram_id(db, telegram_id)
            if not user:
                return False
            await SettingCRUD.update(
                db,
                user.id,
                preferred_pairs=pairs,
            )
            return True
    except Exception as e:
        logger.error(f"Error saving watchlist for {telegram_id}: {e}")
        return False


@router.message(Command("watchlist"))
async def handle_watchlist(message: Message):
    try:
        pairs = await _get_user_watchlist(message.from_user.id)
        text = SignalFormatter.format_watchlist(pairs)

        await message.answer(
            text,
            reply_markup=BotKeyboards.watchlist_menu(pairs),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Error in watchlist handler: {e}")
        await message.answer("❌ Error loading watchlist.")


@router.callback_query(F.data == "watchlist_menu")
async def handle_watchlist_menu_callback(callback: CallbackQuery):
    try:
        pairs = await _get_user_watchlist(callback.from_user.id)
        text = SignalFormatter.format_watchlist(pairs)

        await callback.message.edit_text(
            text,
            reply_markup=BotKeyboards.watchlist_menu(pairs),
            parse_mode="HTML",
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in watchlist menu callback: {e}")
        await callback.answer("❌ Error", show_alert=True)


@router.callback_query(F.data == "watchlist_view")
async def handle_watchlist_view_callback(callback: CallbackQuery):
    try:
        await callback.answer("Loading watchlist...")
        pairs = await _get_user_watchlist(callback.from_user.id)

        if not pairs:
            await callback.message.edit_text(
                "👀 <b>Your Watchlist is Empty</b>\n\n"
                "Add pairs using the button below.\n\n"
                "Example: <code>BTCUSDT</code>, <code>ETHUSDT</code>\n\n"
                "⚡ <i>NEXARA AI</i>",
                parse_mode="HTML",
                reply_markup=BotKeyboards.watchlist_menu(pairs),
            )
            return

        await callback.message.edit_text(
            SignalFormatter.format_watchlist(pairs),
            parse_mode="HTML",
            reply_markup=BotKeyboards.watchlist_pair_buttons(pairs),
        )
    except Exception as e:
        logger.error(f"Error viewing watchlist: {e}")
        await callback.answer("❌ Error", show_alert=True)


@router.callback_query(F.data == "watchlist_add")
async def handle_watchlist_add_callback(callback: CallbackQuery, state: FSMContext):
    try:
        await state.set_state(WatchlistStates.waiting_for_pair)
        await callback.message.edit_text(
            "➕ <b>Add Pair to Watchlist</b>\n\n"
            "Send the pair symbol you want to add.\n\n"
            "<b>Examples:</b>\n"
            "• <code>BTCUSDT</code>\n"
            "• <code>ETHUSDT</code>\n"
            "• <code>SOLUSDT</code>\n"
            "• <code>BNBUSDT</code>\n\n"
            "Send /cancel to cancel.\n\n"
            "⚡ <i>NEXARA AI</i>",
            parse_mode="HTML",
            reply_markup=BotKeyboards.back_button("watchlist_menu"),
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in watchlist add callback: {e}")
        await callback.answer("❌ Error", show_alert=True)


@router.message(WatchlistStates.waiting_for_pair)
async def handle_watchlist_pair_input(message: Message, state: FSMContext):
    try:
        pair = message.text.strip().upper()

        if pair == "/CANCEL":
            await state.clear()
            pairs = await _get_user_watchlist(message.from_user.id)
            await message.answer(
                "❌ <b>Cancelled.</b>",
                parse_mode="HTML",
                reply_markup=BotKeyboards.watchlist_menu(pairs),
            )
            return

        if not pair.endswith("USDT"):
            pair = pair + "USDT"

        if len(pair) < 6 or len(pair) > 15:
            await message.answer(
                "⚠️ <b>Invalid pair format.</b>\n\n"
                "Please send a valid pair like <code>BTCUSDT</code>\n\n"
                "⚡ <i>NEXARA AI</i>",
                parse_mode="HTML",
            )
            return

        pairs = await _get_user_watchlist(message.from_user.id)

        if pair in pairs:
            await state.clear()
            await message.answer(
                f"⚠️ <b>{pair} is already in your watchlist!</b>\n\n"
                "⚡ <i>NEXARA AI</i>",
                parse_mode="HTML",
                reply_markup=BotKeyboards.watchlist_menu(pairs),
            )
            return

        max_pairs = 20
        if len(pairs) >= max_pairs:
            await state.clear()
            await message.answer(
                f"⚠️ <b>Watchlist is full!</b>\n\n"
                f"Maximum {max_pairs} pairs allowed.\n"
                "Remove a pair before adding a new one.\n\n"
                "⚡ <i>NEXARA AI</i>",
                parse_mode="HTML",
                reply_markup=BotKeyboards.watchlist_menu(pairs),
            )
            return

        pairs.append(pair)
        saved = await _save_user_watchlist(message.from_user.id, pairs)

        await state.clear()

        if saved:
            await message.answer(
                f"✅ <b>{pair} added to watchlist!</b>\n\n"
                f"📋 Total pairs: <code>{len(pairs)}</code>\n\n"
                "⚡ <i>NEXARA AI</i>",
                parse_mode="HTML",
                reply_markup=BotKeyboards.watchlist_menu(pairs),
            )
        else:
            await message.answer(
                "❌ <b>Error saving watchlist.</b>\n\n"
                "Please try again.\n\n"
                "⚡ <i>NEXARA AI</i>",
                parse_mode="HTML",
                reply_markup=BotKeyboards.watchlist_menu(pairs),
            )

    except Exception as e:
        logger.error(f"Error handling watchlist pair input: {e}")
        await state.clear()
        await message.answer("❌ Error adding pair. Please try again.")


@router.callback_query(F.data == "watchlist_remove")
async def handle_watchlist_remove_callback(callback: CallbackQuery, state: FSMContext):
    try:
        pairs = await _get_user_watchlist(callback.from_user.id)

        if not pairs:
            await callback.answer("Your watchlist is empty!", show_alert=True)
            return

        await state.set_state(WatchlistStates.waiting_for_remove)
        pairs_list = "\n".join([f"• <code>{p}</code>" for p in pairs])

        await callback.message.edit_text(
            f"🗑️ <b>Remove Pair from Watchlist</b>\n\n"
            f"<b>Your pairs:</b>\n{pairs_list}\n\n"
            f"Send the pair name to remove.\n\n"
            f"Send /cancel to cancel.\n\n"
            f"⚡ <i>NEXARA AI</i>",
            parse_mode="HTML",
            reply_markup=BotKeyboards.back_button("watchlist_menu"),
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in watchlist remove callback: {e}")
        await callback.answer("❌ Error", show_alert=True)


@router.message(WatchlistStates.waiting_for_remove)
async def handle_watchlist_remove_input(message: Message, state: FSMContext):
    try:
        pair = message.text.strip().upper()

        if pair == "/CANCEL":
            await state.clear()
            pairs = await _get_user_watchlist(message.from_user.id)
            await message.answer(
                "❌ <b>Cancelled.</b>",
                parse_mode="HTML",
                reply_markup=BotKeyboards.watchlist_menu(pairs),
            )
            return

        if not pair.endswith("USDT"):
            pair = pair + "USDT"

        pairs = await _get_user_watchlist(message.from_user.id)

        if pair not in pairs:
            await message.answer(
                f"⚠️ <b>{pair} is not in your watchlist!</b>\n\n"
                "⚡ <i>NEXARA AI</i>",
                parse_mode="HTML",
            )
            return

        pairs.remove(pair)
        saved = await _save_user_watchlist(message.from_user

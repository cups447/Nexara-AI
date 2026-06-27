import aiohttp
import asyncio
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from config.settings import settings
from database.connection import AsyncSessionLocal
from database.crud import SignalCRUD, UserCRUD
from bot.keyboards.menus import BotKeyboards
from utils.logger import logger
from utils.formatters import SignalFormatter
from utils.retry import retry_async

router = Router()

_scanner_ref = None


def set_scanner(scanner):
    global _scanner_ref
    _scanner_ref = scanner


@retry_async(max_attempts=3, min_wait=1.0, max_wait=5.0)
async def _fetch_fear_greed() -> dict:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                settings.ALTERNATIVE_ME_API_URL,
                params={"limit": 1},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data and "data" in data and data["data"]:
                        item = data["data"][0]
                        return {
                            "value": int(item.get("value", 50)),
                            "value_classification": item.get("value_classification", "Neutral"),
                            "timestamp": datetime.utcfromtimestamp(
                                int(item.get("timestamp", 0))
                            ).strftime("%Y-%m-%d %H:%M UTC"),
                        }
        return {
            "value": 50,
            "value_classification": "Neutral",
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        }
    except Exception as e:
        logger.error(f"Error fetching fear greed: {e}")
        return {
            "value": 50,
            "value_classification": "Neutral",
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        }


@retry_async(max_attempts=3, min_wait=1.0, max_wait=5.0)
async def _fetch_crypto_news(query: str = "crypto") -> list:
    try:
        async with aiohttp.ClientSession() as session:
            params = {
                "tickers": query.upper(),
                "items": 8,
                "token": settings.CRYPTO_NEWS_API_KEY,
            }
            async with session.get(
                settings.CRYPTO_NEWS_API_URL,
                params=params,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    articles = []
                    for item in data.get("data", [])[:8]:
                        sentiment = item.get("sentiment", "Neutral").lower()
                        articles.append({
                            "title": item.get("title", "No title"),
                            "source": item.get("source_name", "Unknown"),
                            "url": item.get("news_url", ""),
                            "sentiment": sentiment,
                            "date": item.get("date", ""),
                        })
                    return articles
        return _get_mock_news()
    except Exception as e:
        logger.error(f"Error fetching crypto news: {e}")
        return _get_mock_news()


def _get_mock_news() -> list:
    return [
        {
            "title": "Bitcoin consolidates near key resistance level",
            "source": "CryptoNews",
            "url": "",
            "sentiment": "neutral",
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
        },
        {
            "title": "Ethereum network activity reaches new highs",
            "source": "CoinDesk",
            "url": "",
            "sentiment": "positive",
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
        },
        {
            "title": "Crypto market shows signs of recovery amid global uncertainty",
            "source": "CoinTelegraph",
            "url": "",
            "sentiment": "positive",
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
        },
    ]


async def _fetch_market_overview() -> dict:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{settings.COINGECKO_API_URL}/global",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    market_data = data.get("data", {})
                    return {
                        "total_market_cap": market_data.get("total_market_cap", {}).get("usd", 0),
                        "total_volume": market_data.get("total_volume", {}).get("usd", 0),
                        "btc_dominance": market_data.get("market_cap_percentage", {}).get("btc", 0),
                        "eth_dominance": market_data.get("market_cap_percentage", {}).get("eth", 0),
                        "active_coins": market_data.get("active_cryptocurrencies", 0),
                        "market_cap_change_24h": market_data.get("market_cap_change_percentage_24h_usd", 0),
                    }
        return {}
    except Exception as e:
        logger.error(f"Error fetching market overview: {e}")
        return {}


@router.message(Command("fear"))
async def handle_fear(message: Message):
    try:
        loading_msg = await message.answer(
            "⏳ <b>Loading Fear & Greed Index...</b>",
            parse_mode="HTML",
        )

        data = await _fetch_fear_greed()
        text = SignalFormatter.format_fear_greed(data)

        await loading_msg.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=BotKeyboards.refresh_button("fear_greed"),
        )
    except Exception as e:
        logger.error(f"Error in fear handler: {e}")
        await message.answer("❌ Error loading Fear & Greed Index.")


@router.callback_query(F.data == "fear_greed")
async def handle_fear_greed_callback(callback: CallbackQuery):
    try:
        await callback.answer("Loading Fear & Greed...")
        data = await _fetch_fear_greed()
        text = SignalFormatter.format_fear_greed(data)

        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=BotKeyboards.refresh_button("fear_greed"),
        )
    except Exception as e:
        logger.error(f"Error in fear greed callback: {e}")
        await callback.answer("❌ Error loading data", show_alert=True)


@router.message(Command("news"))
async def handle_news(message: Message):
    try:
        await message.answer(
            "📰 <b>NEXARA AI — Crypto News</b>\n\n"
            "Choose a news category:",
            reply_markup=BotKeyboards.news_menu(),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Error in news handler: {e}")
        await message.answer("❌ Error loading news menu.")


@router.callback_query(F.data == "news_latest")
async def handle_news_latest_callback(callback: CallbackQuery):
    try:
        await callback.answer("Loading latest news...")
        loading_msg = await callback.message.edit_text(
            "⏳ <b>Loading latest crypto news...</b>",
            parse_mode="HTML",
        )

        articles = await _fetch_crypto_news("crypto")
        text = SignalFormatter.format_news(articles)

        await loading_msg.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=BotKeyboards.news_menu(),
            disable_web_page_preview=True,
        )
    except Exception as e:
        logger.error(f"Error in news latest callback: {e}")
        await callback.answer("❌ Error loading news", show_alert=True)


@router.callback_query(F.data == "news_trending")
async def handle_news_trending_callback(callback: CallbackQuery):
    try:
        await callback.answer("Loading trending news...")
        loading_msg = await callback.message.edit_text(
            "⏳ <b>Loading trending crypto news...</b>",
            parse_mode="HTML",
        )

        articles = await _fetch_crypto_news("bitcoin,ethereum,crypto")
        text = SignalFormatter.format_news(articles)

        await loading_msg.edit_text(
            f"🔥 <b>TRENDING CRYPTO NEWS</b>\n\n" + text,
            parse_mode="HTML",
            reply_markup=BotKeyboards.news_menu(),
            disable_web_page_preview=True,
        )
    except Exception as e:
        logger.error(f"Error in trending news callback: {e}")
        await callback.answer("❌ Error loading news", show_alert=True)


@router.callback_query(F.data == "news_btc")
async def handle_news_btc_callback(callback: CallbackQuery):
    try:
        await callback.answer("Loading Bitcoin news...")
        loading_msg = await callback.message.edit_text(
            "⏳ <b>Loading Bitcoin news...</b>",
            parse_mode="HTML",
        )

        articles = await _fetch_crypto_news("BTC")
        text = SignalFormatter.format_news(articles)

        await loading_msg.edit_text(
            f"₿ <b>BITCOIN NEWS</b>\n\n" + text,
            parse_mode="HTML",
            reply_markup=BotKeyboards.news_menu(),
            disable_web_page_preview=True,
        )
    except Exception as e:
        logger.error(f"Error in BTC news callback: {e}")
        await callback.answer("❌ Error loading news", show_alert=True)


@router.callback_query(F.data == "news_eth")
async def handle_news_eth_callback(callback: CallbackQuery):
    try:
        await callback.answer("Loading Ethereum news...")
        loading_msg = await callback.message.edit_text(
            "⏳ <b>Loading Ethereum news...</b>",
            parse_mode="HTML",
        )

        articles = await _fetch_crypto_news("ETH")
        text = SignalFormatter.format_news(articles)

        await loading_msg.edit_text(
            f"Ξ <b>ETHEREUM NEWS</b>\n\n" + text,
            parse_mode="HTML",
            reply_markup=BotKeyboards.news_menu(),
            disable_web_page_preview=True,
        )
    except Exception as e:
        logger.error(f"Error in ETH news callback: {e}")
        await callback.answer("❌ Error loading news", show_alert=True)


@router.callback_query(F.data == "news_refresh")
async def handle_news_refresh_callback(callback: CallbackQuery):
    try:
        await handle_news_latest_callback(callback)
    except Exception as e:
        logger.error(f"Error refreshing news: {e}")
        await callback.answer("❌ Error refreshing", show_alert=True)


@router.message(Command("status"))
async def handle_status(message: Message):
    try:
        loading_msg = await message.answer(
            "⏳ <b>Loading system status...</b>",
            parse_mode="HTML",
        )

        if _scanner_ref:
            status = _scanner_ref.get_status()
        else:
            status = {
                "running": False,
                "scan_count": 0,
                "pairs_scanned": 0,
                "signals_found": 0,
                "last_scan": "Not started",
                "next_scan": "Pending",
                "scan_duration_ms": 0,
                "uptime": "00:00:00",
            }

        async with AsyncSessionLocal() as db:
            total_signals = await SignalCRUD.count_today(db)
            win_rate = await SignalCRUD.get_win_rate(db)
            total_users = await UserCRUD.count_all(db)

        market_overview = await _fetch_market_overview()

        market_cap = market_overview.get("total_market_cap", 0)
        market_cap_str = (
            f"${market_cap / 1e12:.2f}T" if market_cap >= 1e12
            else f"${market_cap / 1e9:.2f}B" if market_cap >= 1e9
            else f"${market_cap:,.0f}"
        )

        total_volume = market_overview.get("total_volume", 0)
        volume_str = (
            f"${total_volume / 1e9:.2f}B" if total_volume >= 1e9
            else f"${total_volume:,.0f}"
        )

        scanner_status = "🟢 Running" if status.get("running") else "🔴 Stopped"

        text = (
            f"📡 <b>NEXARA AI — System Status</b>\n"
            f"{'─' * 32}\n"
            f"🤖 <b>Scanner:</b> {scanner_status}\n"
            f"🔄 <b>Scans Done:</b> <code>{status.get('scan_count', 0)}</code>\n"
            f"📊 <b>Pairs Scanned:</b> <code>{status.get('pairs_scanned', 0)}</code>\n"
            f"⏱️ <b>Scan Duration:</b> <code>{status.get('scan_duration_ms', 0):.0f}ms</code>\n"
            f"🕐 <b>Last Scan:</b> <code>{status.get('last_scan', 'Never')}</code>\n"
            f"🔄 <b>Next Scan:</b> <code>{status.get('next_scan', 'Unknown')}</code>\n"
            f"⬆️ <b>Uptime:</b> <code>{status.get('uptime', '00:00:00')}</code>\n"
            f"{'─' * 32}\n"
            f"📈 <b>Today's Signals:</b> <code>{total_signals}</code>\n"
            f"🎯 <b>Win Rate:</b> <code>{win_rate:.1f}%</code>\n"
            f"👥 <b>Total Users:</b> <code>{total_users}</code>\n"
            f"{'─' * 32}\n"
            f"🌍 <b>Market Overview:</b>\n"
            f"  💰 Market Cap: <code>{market_cap_str}</code>\n"
            f"  📊 24H Volume: <code>{volume_str}</code>\n"
            f"  ₿ BTC Dom: <code>{market_overview.get('btc_dominance', 0):.1f}%</code>\n"
            f"  Ξ ETH Dom: <code>{market_overview.get('eth_dominance', 0):.1f}%</code>\n"
            f"  📉 24H Change: <code>{market_overview.get('market_cap_change_24h', 0):+.2f}%</code>\n"
            f"{'─' * 32}\n"
            f"<i>⚡ NEXARA AI | {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</i>"
        )

        await loading_msg.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=BotKeyboards.status_menu(),
        )
    except Exception as e:
        logger.error(f"Error in status handler: {e}")
        await message.answer("❌ Error loading status.")


@router.callback_query(F.data == "status_refresh")
async def handle_status_refresh_callback(callback: CallbackQuery):
    try:
        await callback.answer("Refreshing status...")

        if _scanner_ref:
            status = _scanner_ref.get_status()
        else:
            status = {
                "running": False,
                "scan_count": 0,
                "pairs_scanned": 0,
                "signals_found": 0,
                "last_scan": "Not started",
                "next_scan": "Pending",
                "scan_duration_ms": 0,
                "uptime": "00:00:00",
            }

        async with AsyncSessionLocal() as db:
            total_signals = await SignalCRUD.count_today(db)
            win_rate = await SignalCRUD.get_win_rate(db)
            total_users = await UserCRUD.count_all(db)

        scanner_status = "🟢 Running" if status.get("running") else "🔴 Stopped"

        text = (
            f"📡 <b>NEXARA AI — System Status</b>\n"
            f"{'─' * 32}\n"
            f"🤖 <b>Scanner:</b> {scanner_status}\n"
            f"🔄 <b>Scans Done:</b> <code>{status.get('scan_count', 0)}</code>\n"
            f"📊 <b>Pairs Scanned:</b> <code>{status.get('pairs_scanned', 0)}</code>\n"
            f"⏱️ <b>Scan Duration:</b> <code>{status.get('scan_duration_ms', 0):.0f}ms</code>\n"
            f"🕐 <b>Last Scan:</b> <code>{status.get('last_scan', 'Never')}</code>\n"
            f"🔄 <b>Next Scan:</b> <code>{status.get('next_scan', 'Unknown')}</code>\n"
            f"⬆️ <b>Uptime:</b> <code>{status.get('uptime', '00:00:00')}</code>\n"
            f"{'─' * 32}\n"
            f"📈 <b>Today's Signals:</b> <code>{total_signals}</code>\n"
            f"🎯 <b>Win Rate:</b> <code>{win_rate:.1f}%</code>\n"
            f"👥 <b>Total Users:</b> <code>{total_users}</code>\n"
            f"{'─' * 32}\n"
            f"<i>⚡ NEXARA AI | {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</i>"
        )

        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=BotKeyboards.status_menu(),
        )
    except Exception as e:
        logger.error(f"Error in status refresh callback: {e}")
        await callback.answer("❌ Error refreshing status", show_alert=True)


@router.callback_query(F.data == "status_stats")
async def handle_status_stats_callback(callback: CallbackQuery):
    try:
        await callback.answer("Loading statistics...")

        async with AsyncSessionLocal() as db:
            total_signals_today = await SignalCRUD.count_today(db)
            win_rate = await SignalCRUD.get_win_rate(db)
            top_signals = await SignalCRUD.get_top(db, limit=5, hours=24)
            total_users = await UserCRUD.count_all(db)

        top_pairs = [s.pair for s in top_signals]
        top_pairs_str = ", ".join(top_pairs[:5]) if top_pairs else "None yet"

        text = (
            f"📊 <b>NEXARA AI — Statistics</b>\n"
            f"{'─' * 32}\n"
            f"📈 <b>Today's Signals:</b> <code>{total_signals_today}</code>\n"
            f"🎯 <b>Overall Win Rate:</b> <code>{win_rate:.1f}%</code>\n"
            f"👥 <b>Total Users:</b> <code>{total_users}</code>\n"
            f"{'─' * 32}\n"
            f"🔥 <b>Top Pairs Today:</b>\n"
            f"  <code>{top_pairs_str}</code>\n"
            f"{'─' * 32}\n"
            f"⚙️ <b>Scanner Config:</b>\n"
            f"  Scan Interval: <code>{settings.SCAN_INTERVAL_SECONDS}s</code>\n"
            f"  Min Confidence: <code>{settings.MIN_CONFIDENCE_SCORE}%</code>\n"
            f"  Min Volume: <code>${settings.MIN_VOLUME_USDT:,.0f}</code>\n"
            f"  Max Pairs: <code>{settings.MAX_PAIRS_TO_SCAN}</code>\n"
            f"  Timeframes: <code>{', '.join(settings.PRIMARY_TIMEFRAMES)}</code>\n"
            f"{'─' * 32}\n"
            f"<i>⚡ NEXARA AI | {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</i>"
        )

        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=BotKeyboards.status_menu(),
        )
    except Exception as e:
        logger.error(f"Error in stats callback: {e}")
        await callback.answer("❌ Error loading stats", show_alert=True)


@router.callback_query(F.data == "status_logs")
async def handle_status_logs_callback(callback: CallbackQuery):
    try:
        await callback.answer("Loading recent logs...")

        from database.crud import LogCRUD

        async with AsyncSessionLocal() as db:
            logs = await LogCRUD.get_recent(db, limit=10)

        if not logs:
            await callback.message.edit_text(
                "📋 <b>Recent Logs</b>\n\n"
                "No logs found.\n\n"
                "⚡ <i>NEXARA AI</i>",
                parse_mode="HTML",
                reply_markup=BotKeyboards.status_menu(),
            )
            return

        text = "📋 <b>Recent System Logs</b>\n" + "─" * 32 + "\n"

        for log in logs:
            level_emoji = {
                "INFO": "ℹ️",
                "WARNING": "⚠️",
                "ERROR": "❌",
                "DEBUG": "🔍",
            }.get(log.level, "📝")

            timestamp = log.created_at.strftime("%H:%M:%S") if log.created_at else "Unknown"
            message_short = log.message[:80] + "..." if len(log.message) > 80 else log.message

            text += (
                f"{level_emoji} <code>[{timestamp}]</code> "
                f"<b>{log.level}</b>\n"
                f"  {message_short}\n\n"
            )

        text += f"<i>⚡ NEXARA AI | {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</i>"

        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=BotKeyboards.status_menu(),
        )
    except Exception as e:
        logger.error(f"Error in logs callback: {e}")
        await callback.answer("❌ Error loading logs", show_alert=True)


__all__ = ["router", "set_scanner"]

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from typing import List, Optional, Dict, Any


class BotKeyboards:

    @staticmethod
    def main_menu() -> ReplyKeyboardMarkup:
        builder = ReplyKeyboardBuilder()
        builder.row(
            KeyboardButton(text="📊 Signals"),
            KeyboardButton(text="🔥 Top Signals"),
        )
        builder.row(
            KeyboardButton(text="🔍 Scan"),
            KeyboardButton(text="👀 Watchlist"),
        )
        builder.row(
            KeyboardButton(text="📰 News"),
            KeyboardButton(text="😱 Fear & Greed"),
        )
        builder.row(
            KeyboardButton(text="⚙️ Settings"),
            KeyboardButton(text="📡 Status"),
        )
        return builder.as_markup(
            resize_keyboard=True,
            persistent=True,
        )

    @staticmethod
    def signals_menu() -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="🟢 LONG Signals", callback_data="signals_long"),
            InlineKeyboardButton(text="🔴 SHORT Signals", callback_data="signals_short"),
        )
        builder.row(
            InlineKeyboardButton(text="🔥 Top 10", callback_data="signals_top"),
            InlineKeyboardButton(text="📊 All Active", callback_data="signals_active"),
        )
        builder.row(
            InlineKeyboardButton(text="⏱️ 15m", callback_data="signals_tf_15m"),
            InlineKeyboardButton(text="⏱️ 1H", callback_data="signals_tf_1h"),
            InlineKeyboardButton(text="⏱️ 4H", callback_data="signals_tf_4h"),
        )
        builder.row(
            InlineKeyboardButton(text="🔄 Refresh", callback_data="signals_refresh"),
            InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"),
        )
        return builder.as_markup()

    @staticmethod
    def signal_detail(signal_id: int) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="📊 Full Analysis", callback_data=f"signal_analysis_{signal_id}"),
            InlineKeyboardButton(text="⚠️ Set Alert", callback_data=f"signal_alert_{signal_id}"),
        )
        builder.row(
            InlineKeyboardButton(text="🔄 Refresh", callback_data=f"signal_refresh_{signal_id}"),
            InlineKeyboardButton(text="◀️ Back", callback_data="signals_active"),
        )
        return builder.as_markup()

    @staticmethod
    def scan_menu() -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="🔍 Scan All Pairs", callback_data="scan_all"),
            InlineKeyboardButton(text="⚡ Quick Scan", callback_data="scan_quick"),
        )
        builder.row(
            InlineKeyboardButton(text="⏱️ 15m", callback_data="scan_tf_15m"),
            InlineKeyboardButton(text="⏱️ 1H", callback_data="scan_tf_1h"),
            InlineKeyboardButton(text="⏱️ 4H", callback_data="scan_tf_4h"),
        )
        builder.row(
            InlineKeyboardButton(text="📊 Scan Status", callback_data="scan_status"),
            InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"),
        )
        return builder.as_markup()

    @staticmethod
    def watchlist_menu(pairs: Optional[List[str]] = None) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="➕ Add Pair", callback_data="watchlist_add"),
            InlineKeyboardButton(text="🗑️ Remove Pair", callback_data="watchlist_remove"),
        )
        builder.row(
            InlineKeyboardButton(text="🔍 Scan Watchlist", callback_data="watchlist_scan"),
            InlineKeyboardButton(text="📋 View All", callback_data="watchlist_view"),
        )
        builder.row(
            InlineKeyboardButton(text="🗑️ Clear All", callback_data="watchlist_clear"),
            InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"),
        )
        return builder.as_markup()

    @staticmethod
    def watchlist_pair_buttons(pairs: List[str]) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        for pair in pairs[:20]:
            builder.row(
                InlineKeyboardButton(
                    text=f"🔍 {pair}",
                    callback_data=f"scan_pair_{pair}",
                ),
                InlineKeyboardButton(
                    text=f"❌",
                    callback_data=f"watchlist_del_{pair}",
                ),
            )
        builder.row(
            InlineKeyboardButton(text="◀️ Back", callback_data="watchlist_menu"),
        )
        return builder.as_markup()

    @staticmethod
    def settings_menu() -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="🔔 Notifications", callback_data="settings_notifications"),
            InlineKeyboardButton(text="📊 Min Confidence", callback_data="settings_confidence"),
        )
        builder.row(
            InlineKeyboardButton(text="⏱️ Timeframes", callback_data="settings_timeframes"),
            InlineKeyboardButton(text="💰 Risk Settings", callback_data="settings_risk"),
        )
        builder.row(
            InlineKeyboardButton(text="🌍 Language", callback_data="settings_language"),
            InlineKeyboardButton(text="👑 Premium", callback_data="settings_premium"),
        )
        builder.row(
            InlineKeyboardButton(text="🔄 Reset Defaults", callback_data="settings_reset"),
            InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"),
        )
        return builder.as_markup()

    @staticmethod
    def notifications_menu(enabled: bool = True) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        status = "✅ ON" if enabled else "❌ OFF"
        builder.row(
            InlineKeyboardButton(
                text=f"Notifications: {status}",
                callback_data="settings_toggle_notifications",
            )
        )
        builder.row(
            InlineKeyboardButton(text="🔔 Signal Alerts", callback_data="settings_signal_alerts"),
            InlineKeyboardButton(text="📊 Market Alerts", callback_data="settings_market_alerts"),
        )
        builder.row(
            InlineKeyboardButton(text="◀️ Back", callback_data="settings_menu"),
        )
        return builder.as_markup()

    @staticmethod
    def confidence_menu(current: float = 90.0) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        levels = [90, 92, 94, 95, 97]
        for level in levels:
            marker = "✅ " if abs(current - level) < 0.5 else ""
            builder.button(
                text=f"{marker}{level}%",
                callback_data=f"settings_conf_{level}",
            )
        builder.adjust(3, 2)
        builder.row(
            InlineKeyboardButton(text="◀️ Back", callback_data="settings_menu"),
        )
        return builder.as_markup()

    @staticmethod
    def timeframes_menu(selected: Optional[List[str]] = None) -> InlineKeyboardMarkup:
        selected = selected or ["15m", "1h", "4h"]
        builder = InlineKeyboardBuilder()
        all_timeframes = ["1m", "3m", "5m", "15m", "30m", "1h", "4h", "1d"]
        for tf in all_timeframes:
            marker = "✅ " if tf in selected else ""
            builder.button(
                text=f"{marker}{tf}",
                callback_data=f"settings_tf_{tf}",
            )
        builder.adjust(4, 4)
        builder.row(
            InlineKeyboardButton(text="◀️ Back", callback_data="settings_menu"),
        )
        return builder.as_markup()

    @staticmethod
    def risk_menu(current_risk: float = 1.0, current_leverage: int = 10) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="Risk %", callback_data="noop"),
        )
        risk_levels = [0.5, 1.0, 1.5, 2.0]
        for risk in risk_levels:
            marker = "✅ " if abs(current_risk - risk) < 0.01 else ""
            builder.button(
                text=f"{marker}{risk}%",
                callback_data=f"settings_risk_{risk}",
            )
        builder.adjust(4)
        builder.row(
            InlineKeyboardButton(text="Leverage", callback_data="noop"),
        )
        leverage_levels = [5, 10, 15, 20]
        for lev in leverage_levels:
            marker = "✅ " if current_leverage == lev else ""
            builder.button(
                text=f"{marker}{lev}x",
                callback_data=f"settings_lev_{lev}",
            )
        builder.adjust(4)
        builder.row(
            InlineKeyboardButton(text="◀️ Back", callback_data="settings_menu"),
        )
        return builder.as_markup()

    @staticmethod
    def premium_menu(is_premium: bool = False) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        if not is_premium:
            builder.row(
                InlineKeyboardButton(text="👑 Monthly - $29", callback_data="premium_monthly"),
                InlineKeyboardButton(text="👑 Quarterly - $69", callback_data="premium_quarterly"),
            )
            builder.row(
                InlineKeyboardButton(text="👑 Yearly - $199", callback_data="premium_yearly"),
            )
        else:
            builder.row(
                InlineKeyboardButton(text="✅ Premium Active", callback_data="premium_status"),
            )
            builder.row(
                InlineKeyboardButton(text="🔄 Renew", callback_data="premium_renew"),
            )
        builder.row(
            InlineKeyboardButton(text="◀️ Back", callback_data="settings_menu"),
        )
        return builder.as_markup()

    @staticmethod
    def news_menu() -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="📰 Latest News", callback_data="news_latest"),
            InlineKeyboardButton(text="🔥 Trending", callback_data="news_trending"),
        )
        builder.row(
            InlineKeyboardButton(text="₿ Bitcoin", callback_data="news_btc"),
            InlineKeyboardButton(text="Ξ Ethereum", callback_data="news_eth"),
        )
        builder.row(
            InlineKeyboardButton(text="😱 Fear & Greed", callback_data="fear_greed"),
            InlineKeyboardButton(text="🔄 Refresh", callback_data="news_refresh"),
        )
        builder.row(
            InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"),
        )
        return builder.as_markup()

    @staticmethod
    def status_menu() -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="🔄 Refresh Status", callback_data="status_refresh"),
            InlineKeyboardButton(text="📊 Statistics", callback_data="status_stats"),
        )
        builder.row(
            InlineKeyboardButton(text="📋 Recent Logs", callback_data="status_logs"),
            InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"),
        )
        return builder.as_markup()

    @staticmethod
    def confirm_menu(action: str, item: str = "") -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="✅ Confirm",
                callback_data=f"confirm_{action}_{item}",
            ),
            InlineKeyboardButton(
                text="❌ Cancel",
                callback_data="cancel_action",
            ),
        )
        return builder.as_markup()

    @staticmethod
    def pair_scan_result(pair: str, has_signal: bool = False) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        if has_signal:
            builder.row(
                InlineKeyboardButton(
                    text="📊 View Signal",
                    callback_data=f"view_signal_{pair}",
                ),
            )
        builder.row(
            InlineKeyboardButton(
                text="🔁 Rescan",
                callback_data=f"scan_pair_{pair}",
            ),
            InlineKeyboardButton(
                text="➕ Add to Watchlist",
                callback_data=f"watchlist_add_{pair}",
            ),
        )
        builder.row(
            InlineKeyboardButton(text="◀️ Back", callback_data="scan_menu"),
        )
        return builder.as_markup()

    @staticmethod
    def back_button(callback: str = "main_menu") -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="◀️ Back", callback_data=callback),
        )
        return builder.as_markup()

    @staticmethod
    def refresh_button(callback: str) -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="🔄 Refresh", callback_data=callback),
            InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"),
        )
        return builder.as_markup()

    @staticmethod
    def admin_menu() -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="👥 Users", callback_data="admin_users"),
            InlineKeyboardButton(text="📊 Stats", callback_data="admin_stats"),
        )
        builder.row(
            InlineKeyboardButton(text="📡 Scanner", callback_data="admin_scanner"),
            InlineKeyboardButton(text="📋 Logs", callback_data="admin_logs"),
        )
        builder.row(
            InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast"),
            InlineKeyboardButton(text="🔄 Restart", callback_data="admin_restart"),
        )
        builder.row(
            InlineKeyboardButton(text="🏠 Main Menu", callback_data="main_menu"),
        )
        return builder.as_markup()

    @staticmethod
    def language_menu(current: str = "en") -> InlineKeyboardMarkup:
        builder = InlineKeyboardBuilder()
        languages = [
            ("🇺🇸 English", "en"),
            ("🇫🇷 French", "fr"),
            ("🇪🇸 Spanish", "es"),
            ("🇩🇪 German", "de"),
            ("🇷🇺 Russian", "ru"),
            ("🇨🇳 Chinese", "zh"),
            ("🇯🇵 Japanese", "ja"),
            ("🇦🇷 Arabic", "ar"),
        ]
        for name, code in languages:
            marker = "✅ " if current == code else ""
            builder.button(
                text=f"{marker}{name}",
                callback_data=f"settings_lang_{code}",
            )
        builder.adjust(2)
        builder.row(
            InlineKeyboardButton(text="◀️ Back", callback_data="settings_menu"),
        )
        return builder.as_markup()


__all__ = ["BotKeyboards"]

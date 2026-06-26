from datetime import datetime
from typing import Optional, List, Dict, Any
from utils.logger import logger


class SignalFormatter:

    LONG_EMOJI = "🟢"
    SHORT_EMOJI = "🔴"
    NEUTRAL_EMOJI = "⚪"
    FIRE_EMOJI = "🔥"
    ROCKET_EMOJI = "🚀"
    WARNING_EMOJI = "⚠️"
    CHART_EMOJI = "📊"
    CLOCK_EMOJI = "⏱️"
    DIAMOND_EMOJI = "💎"
    SHIELD_EMOJI = "🛡️"
    TARGET_EMOJI = "🎯"
    LIGHTNING_EMOJI = "⚡"
    STAR_EMOJI = "⭐"
    CROWN_EMOJI = "👑"

    @staticmethod
    def format_signal(signal: Dict[str, Any]) -> str:
        direction = signal.get("direction", "LONG")
        direction_emoji = SignalFormatter.LONG_EMOJI if direction == "LONG" else SignalFormatter.SHORT_EMOJI
        confidence = signal.get("confidence", 0.0)
        pair = signal.get("pair", "UNKNOWN")
        timeframe = signal.get("timeframe", "15m")
        entry = signal.get("entry", 0.0)
        sl = signal.get("stop_loss", 0.0)
        tp1 = signal.get("tp1", 0.0)
        tp2 = signal.get("tp2", 0.0)
        tp3 = signal.get("tp3", 0.0)
        rr = signal.get("risk_reward", 0.0)
        trend = signal.get("trend", "NEUTRAL")
        reasons = signal.get("reasons", [])
        indicators = signal.get("indicators_passed", [])
        smc = signal.get("smc_confirmation", [])
        win_rate = signal.get("estimated_win_rate", 0.0)
        duration = signal.get("trade_duration", "Unknown")

        confidence_stars = SignalFormatter._confidence_stars(confidence)
        trend_emoji = SignalFormatter._trend_emoji(trend)

        reasons_text = "\n".join([f"  • {r}" for r in reasons]) if reasons else "  • No reasons provided"
        indicators_text = " | ".join(indicators) if indicators else "None"
        smc_text = " | ".join(smc) if smc else "None"

        message = (
            f"{SignalFormatter.ROCKET_EMOJI} <b>NEXARA AI SIGNAL</b> {SignalFormatter.ROCKET_EMOJI}\n"
            f"{'─' * 32}\n"
            f"{direction_emoji} <b>Pair:</b> <code>{pair}</code>  [{timeframe}]\n"
            f"{direction_emoji} <b>Direction:</b> <b>{direction}</b>\n"
            f"{'─' * 32}\n"
            f"{SignalFormatter.TARGET_EMOJI} <b>Entry:</b> <code>{SignalFormatter._format_price(entry)}</code>\n"
            f"{SignalFormatter.SHIELD_EMOJI} <b>Stop Loss:</b> <code>{SignalFormatter._format_price(sl)}</code>\n"
            f"{'─' * 32}\n"
            f"{SignalFormatter.FIRE_EMOJI} <b>TP1:</b> <code>{SignalFormatter._format_price(tp1)}</code>\n"
            f"{SignalFormatter.FIRE_EMOJI} <b>TP2:</b> <code>{SignalFormatter._format_price(tp2)}</code>\n"
            f"{SignalFormatter.FIRE_EMOJI} <b>TP3:</b> <code>{SignalFormatter._format_price(tp3)}</code>\n"
            f"{'─' * 32}\n"
            f"{SignalFormatter.CHART_EMOJI} <b>Risk/Reward:</b> <code>1:{rr:.2f}</code>\n"
            f"{SignalFormatter.DIAMOND_EMOJI} <b>Confidence:</b> <code>{confidence:.1f}%</code> {confidence_stars}\n"
            f"{trend_emoji} <b>Trend:</b> <code>{trend}</code>\n"
            f"{'─' * 32}\n"
            f"{SignalFormatter.LIGHTNING_EMOJI} <b>Reasons:</b>\n{reasons_text}\n"
            f"{'─' * 32}\n"
            f"{SignalFormatter.STAR_EMOJI} <b>Indicators Passed:</b>\n  <code>{indicators_text}</code>\n"
            f"{SignalFormatter.CROWN_EMOJI} <b>SMC Confirmation:</b>\n  <code>{smc_text}</code>\n"
            f"{'─' * 32}\n"
            f"{SignalFormatter.TARGET_EMOJI} <b>Est. Win Rate:</b> <code>{win_rate:.1f}%</code>\n"
            f"{SignalFormatter.CLOCK_EMOJI} <b>Trade Duration:</b> <code>{duration}</code>\n"
            f"{'─' * 32}\n"
            f"<i>⚡ Powered by NEXARA AI | {SignalFormatter._now()}</i>"
        )

        return message

    @staticmethod
    def format_top_signals(signals: List[Dict[str, Any]]) -> str:
        if not signals:
            return f"{SignalFormatter.WARNING_EMOJI} <b>No top signals available right now.</b>"

        lines = [
            f"{SignalFormatter.CROWN_EMOJI} <b>NEXARA AI — TOP SIGNALS</b> {SignalFormatter.CROWN_EMOJI}\n"
            f"{'─' * 32}\n"
        ]

        for i, signal in enumerate(signals[:10], 1):
            direction = signal.get("direction", "LONG")
            d_emoji = SignalFormatter.LONG_EMOJI if direction == "LONG" else SignalFormatter.SHORT_EMOJI
            pair = signal.get("pair", "UNKNOWN")
            confidence = signal.get("confidence", 0.0)
            entry = signal.get("entry", 0.0)
            rr = signal.get("risk_reward", 0.0)
            timeframe = signal.get("timeframe", "15m")

            lines.append(
                f"{i}. {d_emoji} <b>{pair}</b> [{timeframe}]\n"
                f"   Entry: <code>{SignalFormatter._format_price(entry)}</code> | "
                f"RR: <code>1:{rr:.1f}</code> | "
                f"Conf: <code>{confidence:.1f}%</code>\n"
            )

        lines.append(f"\n<i>⚡ NEXARA AI | {SignalFormatter._now()}</i>")
        return "".join(lines)

    @staticmethod
    def format_scan_status(status: Dict[str, Any]) -> str:
        pairs_scanned = status.get("pairs_scanned", 0)
        signals_found = status.get("signals_found", 0)
        last_scan = status.get("last_scan", "Never")
        next_scan = status.get("next_scan", "Unknown")
        uptime = status.get("uptime", "Unknown")
        scan_duration = status.get("scan_duration_ms", 0)

        return (
            f"{SignalFormatter.CHART_EMOJI} <b>NEXARA AI — SCAN STATUS</b>\n"
            f"{'─' * 32}\n"
            f"📡 <b>Pairs Scanned:</b> <code>{pairs_scanned}</code>\n"
            f"🎯 <b>Signals Found:</b> <code>{signals_found}</code>\n"
            f"⏱️ <b>Scan Duration:</b> <code>{scan_duration}ms</code>\n"
            f"🕐 <b>Last Scan:</b> <code>{last_scan}</code>\n"
            f"🔄 <b>Next Scan:</b> <code>{next_scan}</code>\n"
            f"⬆️ <b>Uptime:</b> <code>{uptime}</code>\n"
            f"{'─' * 32}\n"
            f"<i>⚡ NEXARA AI | {SignalFormatter._now()}</i>"
        )

    @staticmethod
    def format_fear_greed(data: Dict[str, Any]) -> str:
        value = data.get("value", 0)
        classification = data.get("value_classification", "Unknown")
        timestamp = data.get("timestamp", "Unknown")

        emoji = SignalFormatter._fear_greed_emoji(value)

        bar = SignalFormatter._progress_bar(value, 100, length=20)

        return (
            f"😱 <b>CRYPTO FEAR & GREED INDEX</b>\n"
            f"{'─' * 32}\n"
            f"{emoji} <b>Value:</b> <code>{value}/100</code>\n"
            f"📊 <b>Sentiment:</b> <code>{classification}</code>\n"
            f"\n{bar}\n"
            f"<code>0 Fear {'':>10} 100 Greed</code>\n"
            f"{'─' * 32}\n"
            f"🕐 <b>Updated:</b> <code>{timestamp}</code>\n"
            f"<i>⚡ NEXARA AI | {SignalFormatter._now()}</i>"
        )

    @staticmethod
    def format_watchlist(pairs: List[str]) -> str:
        if not pairs:
            return f"{SignalFormatter.WARNING_EMOJI} <b>Your watchlist is empty.</b>\nUse /watchlist add BTCUSDT to add pairs."

        lines = [
            f"👀 <b>YOUR WATCHLIST</b>\n"
            f"{'─' * 32}\n"
        ]

        for i, pair in enumerate(pairs, 1):
            lines.append(f"{i}. <code>{pair}</code>\n")

        lines.append(f"\n<i>⚡ NEXARA AI | {SignalFormatter._now()}</i>")
        return "".join(lines)

    @staticmethod
    def format_news(articles: List[Dict[str, Any]]) -> str:
        if not articles:
            return f"{SignalFormatter.WARNING_EMOJI} <b>No news available right now.</b>"

        lines = [f"📰 <b>CRYPTO NEWS</b>\n{'─' * 32}\n"]

        for i, article in enumerate(articles[:8], 1):
            title = article.get("title", "No title")
            source = article.get("source", "Unknown")
            url = article.get("url", "")
            sentiment = article.get("sentiment", "neutral")
            s_emoji = "🟢" if sentiment == "positive" else "🔴" if sentiment == "negative" else "⚪"

            if url:
                lines.append(f"{i}. {s_emoji} <a href='{url}'>{title}</a>\n   <i>{source}</i>\n\n")
            else:
                lines.append(f"{i}. {s_emoji} {title}\n   <i>{source}</i>\n\n")

        lines.append(f"<i>⚡ NEXARA AI | {SignalFormatter._now()}</i>")
        return "".join(lines)

    @staticmethod
    def _format_price(price: float) -> str:
        if price == 0:
            return "0.00"
        if price >= 1000:
            return f"{price:,.2f}"
        elif price >= 1:
            return f"{price:.4f}"
        elif price >= 0.01:
            return f"{price:.6f}"
        else:
            return f"{price:.8f}"

    @staticmethod
    def _confidence_stars(confidence: float) -> str:
        if confidence >= 97:
            return "⭐⭐⭐⭐⭐"
        elif confidence >= 95:
            return "⭐⭐⭐⭐"
        elif confidence >= 93:
            return "⭐⭐⭐"
        elif confidence >= 91:
            return "⭐⭐"
        else:
            return "⭐"

    @staticmethod
    def _trend_emoji(trend: str) -> str:
        trend = trend.upper()
        if trend == "BULLISH":
            return "📈"
        elif trend == "BEARISH":
            return "📉"
        else:
            return "➡️"

    @staticmethod
    def _fear_greed_emoji(value: int) -> str:
        if value <= 20:
            return "😱"
        elif value <= 40:
            return "😟"
        elif value <= 60:
            return "😐"
        elif value <= 80:
            return "😊"
        else:
            return "🤑"

    @staticmethod
    def _progress_bar(value: float, maximum: float, length: int = 20) -> str:
        filled = int((value / maximum) * length)
        bar = "█" * filled + "░" * (length - filled)
        return f"[{bar}]"

    @staticmethod
    def _now() -> str:
        return datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    @staticmethod
    def format_error(message: str) -> str:
        return f"❌ <b>Error:</b> {message}"

    @staticmethod
    def format_success(message: str) -> str:
        return f"✅ <b>Success:</b> {message}"

    @staticmethod
    def format_info(message: str) -> str:
        return f"ℹ️ {message}"


__all__ = ["SignalFormatter"]

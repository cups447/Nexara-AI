from bot.handlers.start import router as start_router
from bot.handlers.signals import router as signals_router
from bot.handlers.scan import router as scan_router
from bot.handlers.watchlist import router as watchlist_router
from bot.handlers.settings import router as settings_router
from bot.handlers.info import router as info_router

__all__ = [
    "start_router",
    "signals_router",
    "scan_router",
    "watchlist_router",
    "settings_router",
    "info_router",
]

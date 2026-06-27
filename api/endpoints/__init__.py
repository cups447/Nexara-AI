from api.endpoints.health import router as health_router
from api.endpoints.signals import router as signals_router
from api.endpoints.scanner import router as scanner_router

__all__ = [
    "health_router",
    "signals_router",
    "scanner_router",
]

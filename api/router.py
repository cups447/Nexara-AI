from fastapi import APIRouter
from api.endpoints.health import router as health_router
from api.endpoints.signals import router as signals_router
from api.endpoints.scanner import router as scanner_router

api_router = APIRouter()

api_router.include_router(
    health_router,
    tags=["Health"],
)

api_router.include_router(
    signals_router,
    prefix="/api/v1",
    tags=["Signals"],
)

api_router.include_router(
    scanner_router,
    prefix="/api/v1",
    tags=["Scanner"],
)


def set_scanner_refs(scanner, signal_engine) -> None:
    from api.endpoints.health import set_scanner as health_set_scanner
    from api.endpoints.scanner import set_scanner as scanner_set_scanner
    health_set_scanner(scanner)
    scanner_set_scanner(scanner, signal_engine)


__all__ = ["api_router", "set_scanner_refs"]

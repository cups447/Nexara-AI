import time
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Optional

from config.settings import settings
from database.connection import check_db_health
from utils.logger import logger

router = APIRouter()

_start_time = time.monotonic()
_scanner_ref = None


def set_scanner(scanner) -> None:
    global _scanner_ref
    _scanner_ref = scanner


def verify_api_key(x_api_key: Optional[str] = Header(None)) -> bool:
    if not x_api_key or x_api_key != settings.API_SECRET_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key",
        )
    return True


@router.get("/health")
async def health_check():
    try:
        db_healthy = await check_db_health()
        uptime_seconds = time.monotonic() - _start_time
        hours = int(uptime_seconds // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        seconds = int(uptime_seconds % 60)

        scanner_status = "unknown"
        if _scanner_ref:
            scanner_status = "running" if _scanner_ref._running else "stopped"

        return {
            "status": "healthy" if db_healthy else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime": f"{hours:02d}:{minutes:02d}:{seconds:02d}",
            "uptime_seconds": round(uptime_seconds, 2),
            "database": "healthy" if db_healthy else "unhealthy",
            "scanner": scanner_status,
            "environment": settings.ENVIRONMENT,
            "version": "1.0.0",
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
        }


@router.get("/health/detailed")
async def detailed_health_check(authorized: bool = Depends(verify_api_key)):
    try:
        db_healthy = await check_db_health()
        uptime_seconds = time.monotonic() - _start_time

        scanner_info = {}
        if _scanner_ref:
            scanner_info = _scanner_ref.get_status()

        from database.connection import AsyncSessionLocal
        from database.crud import SignalCRUD, UserCRUD

        async with AsyncSessionLocal() as db:
            total_signals_today = await SignalCRUD.count_today(db)
            win_rate = await SignalCRUD.get_win_rate(db)
            total_users = await UserCRUD.count_all(db)

        return {
            "status": "healthy" if db_healthy else "degraded",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": round(uptime_seconds, 2),
            "environment": settings.ENVIRONMENT,
            "version": "1.0.0",
            "database": {
                "status": "healthy" if db_healthy else "unhealthy",
                "url": settings.DATABASE_URL.split("///")[0] + "///***",
            },
            "scanner": scanner_info,
            "stats": {
                "signals_today": total_signals_today,
                "win_rate": round(win_rate, 2),
                "total_users": total_users,
            },
            "config": {
                "scan_interval": settings.SCAN_INTERVAL_SECONDS,
                "min_confidence": settings.MIN_CONFIDENCE_SCORE,
                "min_volume_usdt": settings.MIN_VOLUME_USDT,
                "max_pairs": settings.MAX_PAIRS_TO_SCAN,
                "timeframes": settings.PRIMARY_TIMEFRAMES,
            },
        }
    except Exception as e:
        logger.error(f"Detailed health check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ping")
async def ping():
    return {
        "message": "pong",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "NEXARA AI",
    }


@router.get("/version")
async def version():
    return {
        "name": "NEXARA AI",
        "version": "1.0.0",
        "description": "Institutional-grade AI crypto trading platform",
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.utcnow().isoformat(),
    }


__all__ = ["router", "set_scanner"]

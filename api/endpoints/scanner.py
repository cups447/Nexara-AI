from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Header
from pydantic import BaseModel

from config.settings import settings
from utils.logger import logger

router = APIRouter()

_scanner_ref = None
_signal_engine_ref = None


def set_scanner(scanner, signal_engine) -> None:
    global _scanner_ref, _signal_engine_ref
    _scanner_ref = scanner
    _signal_engine_ref = signal_engine


def verify_api_key(x_api_key: Optional[str] = Header(None)) -> bool:
    if not x_api_key or x_api_key != settings.API_SECRET_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key",
        )
    return True


class ScannerStatusResponse(BaseModel):
    running: bool
    scan_count: int
    pairs_scanned: int
    signals_found: int
    last_scan: str
    next_scan: str
    scan_duration_ms: float
    uptime: str
    timestamp: str


class PairScanRequest(BaseModel):
    pair: str
    timeframes: Optional[List[str]] = None


class PairScanResponse(BaseModel):
    pair: str
    timeframes: List[str]
    signals_found: int
    signals: List[dict]
    scan_duration_ms: float
    timestamp: str


class FilteredPairsResponse(BaseModel):
    total: int
    pairs: List[str]
    timestamp: str


class TopMoversResponse(BaseModel):
    total: int
    movers: List[dict]
    timestamp: str


class FundingRateResponse(BaseModel):
    pair: str
    funding_rate: float
    next_funding_time: Optional[str]
    timestamp: str


class OpenInterestResponse(BaseModel):
    pair: str
    open_interest: float
    open_interest_value: float
    timestamp: str


@router.get(
    "/scanner/status",
    response_model=ScannerStatusResponse,
    summary="Get scanner status",
)
async def get_scanner_status(
    authorized: bool = Depends(verify_api_key),
):
    try:
        if _scanner_ref is None:
            return ScannerStatusResponse(
                running=False,
                scan_count=0,
                pairs_scanned=0,
                signals_found=0,
                last_scan="Not started",
                next_scan="Pending",
                scan_duration_ms=0.0,
                uptime="00:00:00",
                timestamp=datetime.utcnow().isoformat(),
            )

        status = _scanner_ref.get_status()

        return ScannerStatusResponse(
            running=status.get("running", False),
            scan_count=status.get("scan_count", 0),
            pairs_scanned=status.get("pairs_scanned", 0),
            signals_found=status.get("signals_found", 0),
            last_scan=status.get("last_scan", "Never"),
            next_scan=status.get("next_scan", "Unknown"),
            scan_duration_ms=status.get("scan_duration_ms", 0.0),
            uptime=status.get("uptime", "00:00:00"),
            timestamp=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        logger.error(f"Error getting scanner status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/scanner/scan/pair",
    response_model=PairScanResponse,
    summary="Scan a specific pair",
)
async def scan_pair(
    request: PairScanRequest,
    authorized: bool = Depends(verify_api_key),
):
    try:
        if _scanner_ref is None or _signal_engine_ref is None:
            raise HTTPException(
                status_code=503,
                detail="Scanner not initialized",
            )

        import time
        start = time.monotonic()

        pair = request.pair.upper()
        timeframes = request.timeframes or settings.PRIMARY_TIMEFRAMES

        results = await _scanner_ref.scan_pair(pair, timeframes)
        signals = await _signal_engine_ref.process_scan_results(results)

        duration_ms = (time.monotonic() - start) * 1000

        from database.connection import AsyncSessionLocal
        from database.crud import SignalCRUD

        saved_signals = []
        for signal in signals:
            async with AsyncSessionLocal() as db:
                is_new = await SignalCRUD.check_cooldown(
                    db,
                    signal["pair"],
                    signal["timeframe"],
                )
            if is_new:
                async with AsyncSessionLocal() as db:
                    saved = await SignalCRUD.create(db, signal)
                saved_signals.append(saved.to_dict())

        return PairScanResponse(
            pair=pair,
            timeframes=timeframes,
            signals_found=len(saved_signals),
            signals=saved_signals,
            scan_duration_ms=round(duration_ms, 2),
            timestamp=datetime.utcnow().isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error scanning pair {request.pair}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/scanner/pairs",
    response_model=FilteredPairsResponse,
    summary="Get filtered trading pairs",
)
async def get_filtered_pairs(
    max_pairs: int = Query(default=200, ge=1, le=500),
    min_volume: float = Query(default=1_000_000.0),
    authorized: bool = Depends(verify_api_key),
):
    try:
        if _scanner_ref is None:
            raise HTTPException(
                status_code=503,
                detail="Scanner not initialized",
            )

        pairs = await _scanner_ref.pair_filter.get_filtered_pairs(
            max_pairs=max_pairs,
            min_volume=min_volume,
        )

        return FilteredPairsResponse(
            total=len(pairs),
            pairs=pairs,
            timestamp=datetime.utcnow().isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting filtered pairs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/scanner/movers",
    response_model=TopMoversResponse,
    summary="Get top movers",
)
async def get_top_movers(
    limit: int = Query(default=20, ge=1, le=50),
    authorized: bool = Depends(verify_api_key),
):
    try:
        if _scanner_ref is None:
            raise HTTPException(
                status_code=503,
                detail="Scanner not initialized",
            )

        pairs = await _scanner_ref.pair_filter.get_filtered_pairs(max_pairs=100)
        movers = await _scanner_ref.pair_filter.get_top_movers(pairs, limit=limit)

        return TopMoversResponse(
            total=len(movers),
            movers=movers,
            timestamp=datetime.utcnow().isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting top movers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/scanner/funding/{pair}",
    response_model=FundingRateResponse,
    summary="Get funding rate for a pair",
)
async def get_funding_rate(
    pair: str,
    authorized: bool = Depends(verify_api_key),
):
    try:
        if _scanner_ref is None:
            raise HTTPException(
                status_code=503,
                detail="Scanner not initialized",
            )

        pair = pair.upper()
        data = await _scanner_ref.pair_filter.get_funding_rate(pair)

        if not data:
            raise HTTPException(
                status_code=404,
                detail=f"Funding rate not found for {pair}",
            )

        next_funding = None
        if data.get("next_funding_time"):
            try:
                next_funding = datetime.utcfromtimestamp(
                    data["next_funding_time"] / 1000
                ).isoformat()
            except Exception:
                next_funding = str(data.get("next_funding_time"))

        return FundingRateResponse(
            pair=pair,
            funding_rate=data.get("funding_rate", 0.0),
            next_funding_time=next_funding,
            timestamp=datetime.utcnow().isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting funding rate for {pair}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/scanner/oi/{pair}",
    response_model=OpenInterestResponse,
    summary="Get open interest for a pair",
)
async def get_open_interest(
    pair: str,
    authorized: bool = Depends(verify_api_key),
):
    try:
        if _scanner_ref is None:
            raise HTTPException(
                status_code=503,
                detail="Scanner not initialized",
            )

        pair = pair.upper()
        data = await _scanner_ref.pair_filter.get_open_interest(pair)

        if not data:
            raise HTTPException(
                status_code=404,
                detail=f"Open interest not found for {pair}",
            )

        return OpenInterestResponse(
            pair=pair,
            open_interest=data.get("open_interest", 0.0),
            open_interest_value=data.get("open_interest_value", 0.0),
            timestamp=datetime.utcnow().isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting open interest for {pair}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/scanner/ticker/{pair}",
    summary="Get ticker data for a pair",
)
async def get_ticker(
    pair: str,
    authorized: bool = Depends(verify_api_key),
):
    try:
        if _scanner_ref is None:
            raise HTTPException(
                status_code=503,
                detail="Scanner not initialized",
            )

        pair = pair.upper()
        data = await _scanner_ref.pair_filter.get_ticker_data(pair)

        if not data:
            raise HTTPException(
                status_code=404,
                detail=f"Ticker not found for {pair}",
            )

        return {
            **data,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting ticker for {pair}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/scanner/scan/quick",
    summary="Run a quick scan on top pairs",
)
async def quick_scan(
    max_pairs: int = Query(default=20, ge=5, le=50),
    authorized: bool = Depends(verify_api_key),
):
    try:
        if _scanner_ref is None or _signal_engine_ref is None:
            raise HTTPException(
                status_code=503,
                detail="Scanner not initialized",
            )

        import time
        start = time.monotonic()

        pairs = await _scanner_ref.pair_filter.get_filtered_pairs(max_pairs=max_pairs)
        results = await _scanner_ref.scan_all_pairs(
            pairs=pairs,
            timeframes=["15m", "1h"],
        )
        signals = await _signal_engine_ref.process_scan_results(results)

        duration_ms = (time.monotonic() - start) * 1000

        from database.connection import AsyncSessionLocal
        from database.crud import SignalCRUD

        saved_signals = []
        for signal in signals:
            async with AsyncSessionLocal() as db:
                is_new = await SignalCRUD.check_cooldown(
                    db,
                    signal["pair"],
                    signal["timeframe"],
                )
            if is_new:
                async with AsyncSessionLocal() as db:
                    saved = await SignalCRUD.create(db, signal)
                saved_signals.append(saved.to_dict())

        return {
            "pairs_scanned": len(pairs),
            "results_analyzed": len(results),
            "signals_found": len(saved_signals),
            "signals": saved_signals,
            "scan_duration_ms": round(duration_ms, 2),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in quick scan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


__all__ = ["router", "set_scanner"]

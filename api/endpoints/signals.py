from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Header
from pydantic import BaseModel

from config.settings import settings
from database.connection import AsyncSessionLocal
from database.crud import SignalCRUD
from utils.logger import logger

router = APIRouter()


def verify_api_key(x_api_key: Optional[str] = Header(None)) -> bool:
    if not x_api_key or x_api_key != settings.API_SECRET_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key",
        )
    return True


class SignalResponse(BaseModel):
    id: int
    pair: str
    direction: str
    timeframe: str
    entry: float
    stop_loss: float
    tp1: float
    tp2: float
    tp3: float
    risk_reward: float
    confidence: float
    trend: str
    reasons: list
    indicators_passed: list
    smc_confirmation: list
    estimated_win_rate: float
    trade_duration: Optional[str]
    is_active: bool
    result: Optional[str]
    profit_loss: Optional[float]
    created_at: Optional[str]
    closed_at: Optional[str]

    class Config:
        from_attributes = True


class SignalListResponse(BaseModel):
    total: int
    signals: List[SignalResponse]
    timestamp: str


class SignalStatsResponse(BaseModel):
    total_signals: int
    signals_today: int
    win_rate: float
    active_signals: int
    timestamp: str


@router.get(
    "/signals",
    response_model=SignalListResponse,
    summary="Get recent signals",
)
async def get_signals(
    limit: int = Query(default=10, ge=1, le=100),
    min_confidence: float = Query(default=90.0, ge=0.0, le=100.0),
    direction: Optional[str] = Query(default=None, regex="^(LONG|SHORT)$"),
    timeframe: Optional[str] = Query(default=None),
    authorized: bool = Depends(verify_api_key),
):
    try:
        async with AsyncSessionLocal() as db:
            signals = await SignalCRUD.get_recent(
                db,
                limit=limit * 3,
                min_confidence=min_confidence,
            )

        if direction:
            signals = [s for s in signals if s.direction == direction]

        if timeframe:
            signals = [s for s in signals if s.timeframe == timeframe]

        signals = signals[:limit]

        signal_list = [
            SignalResponse(
                id=s.id,
                pair=s.pair,
                direction=s.direction,
                timeframe=s.timeframe,
                entry=s.entry,
                stop_loss=s.stop_loss,
                tp1=s.tp1,
                tp2=s.tp2,
                tp3=s.tp3,
                risk_reward=s.risk_reward,
                confidence=s.confidence,
                trend=s.trend,
                reasons=s.get_reasons(),
                indicators_passed=s.get_indicators_passed(),
                smc_confirmation=s.get_smc_confirmation(),
                estimated_win_rate=s.estimated_win_rate,
                trade_duration=s.trade_duration,
                is_active=s.is_active,
                result=s.result,
                profit_loss=s.profit_loss,
                created_at=s.created_at.isoformat() if s.created_at else None,
                closed_at=s.closed_at.isoformat() if s.closed_at else None,
            )
            for s in signals
        ]

        return SignalListResponse(
            total=len(signal_list),
            signals=signal_list,
            timestamp=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        logger.error(f"Error getting signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/signals/top",
    response_model=SignalListResponse,
    summary="Get top signals by confidence",
)
async def get_top_signals(
    limit: int = Query(default=10, ge=1, le=50),
    hours: int = Query(default=24, ge=1, le=168),
    authorized: bool = Depends(verify_api_key),
):
    try:
        async with AsyncSessionLocal() as db:
            signals = await SignalCRUD.get_top(db, limit=limit, hours=hours)

        signal_list = [
            SignalResponse(
                id=s.id,
                pair=s.pair,
                direction=s.direction,
                timeframe=s.timeframe,
                entry=s.entry,
                stop_loss=s.stop_loss,
                tp1=s.tp1,
                tp2=s.tp2,
                tp3=s.tp3,
                risk_reward=s.risk_reward,
                confidence=s.confidence,
                trend=s.trend,
                reasons=s.get_reasons(),
                indicators_passed=s.get_indicators_passed(),
                smc_confirmation=s.get_smc_confirmation(),
                estimated_win_rate=s.estimated_win_rate,
                trade_duration=s.trade_duration,
                is_active=s.is_active,
                result=s.result,
                profit_loss=s.profit_loss,
                created_at=s.created_at.isoformat() if s.created_at else None,
                closed_at=s.closed_at.isoformat() if s.closed_at else None,
            )
            for s in signals
        ]

        return SignalListResponse(
            total=len(signal_list),
            signals=signal_list,
            timestamp=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        logger.error(f"Error getting top signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/signals/active",
    response_model=SignalListResponse,
    summary="Get all active signals",
)
async def get_active_signals(
    authorized: bool = Depends(verify_api_key),
):
    try:
        async with AsyncSessionLocal() as db:
            signals = await SignalCRUD.get_active(db)

        signal_list = [
            SignalResponse(
                id=s.id,
                pair=s.pair,
                direction=s.direction,
                timeframe=s.timeframe,
                entry=s.entry,
                stop_loss=s.stop_loss,
                tp1=s.tp1,
                tp2=s.tp2,
                tp3=s.tp3,
                risk_reward=s.risk_reward,
                confidence=s.confidence,
                trend=s.trend,
                reasons=s.get_reasons(),
                indicators_passed=s.get_indicators_passed(),
                smc_confirmation=s.get_smc_confirmation(),
                estimated_win_rate=s.estimated_win_rate,
                trade_duration=s.trade_duration,
                is_active=s.is_active,
                result=s.result,
                profit_loss=s.profit_loss,
                created_at=s.created_at.isoformat() if s.created_at else None,
                closed_at=s.closed_at.isoformat() if s.closed_at else None,
            )
            for s in signals
        ]

        return SignalListResponse(
            total=len(signal_list),
            signals=signal_list,
            timestamp=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        logger.error(f"Error getting active signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/signals/{signal_id}",
    response_model=SignalResponse,
    summary="Get signal by ID",
)
async def get_signal_by_id(
    signal_id: int,
    authorized: bool = Depends(verify_api_key),
):
    try:
        async with AsyncSessionLocal() as db:
            signal = await SignalCRUD.get_by_id(db, signal_id)

        if not signal:
            raise HTTPException(
                status_code=404,
                detail=f"Signal {signal_id} not found",
            )

        return SignalResponse(
            id=signal.id,
            pair=signal.pair,
            direction=signal.direction,
            timeframe=signal.timeframe,
            entry=signal.entry,
            stop_loss=signal.stop_loss,
            tp1=signal.tp1,
            tp2=signal.tp2,
            tp3=signal.tp3,
            risk_reward=signal.risk_reward,
            confidence=signal.confidence,
            trend=signal.trend,
            reasons=signal.get_reasons(),
            indicators_passed=signal.get_indicators_passed(),
            smc_confirmation=signal.get_smc_confirmation(),
            estimated_win_rate=signal.estimated_win_rate,
            trade_duration=signal.trade_duration,
            is_active=signal.is_active,
            result=signal.result,
            profit_loss=signal.profit_loss,
            created_at=signal.created_at.isoformat() if signal.created_at else None,
            closed_at=signal.closed_at.isoformat() if signal.closed_at else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting signal {signal_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/signals/pair/{pair}",
    response_model=SignalListResponse,
    summary="Get signals for a specific pair",
)
async def get_signals_by_pair(
    pair: str,
    limit: int = Query(default=5, ge=1, le=20),
    authorized: bool = Depends(verify_api_key),
):
    try:
        pair = pair.upper()

        async with AsyncSessionLocal() as db:
            signals = await SignalCRUD.get_by_pair(db, pair, limit=limit)

        signal_list = [
            SignalResponse(
                id=s.id,
                pair=s.pair,
                direction=s.direction,
                timeframe=s.timeframe,
                entry=s.entry,
                stop_loss=s.stop_loss,
                tp1=s.tp1,
                tp2=s.tp2,
                tp3=s.tp3,
                risk_reward=s.risk_reward,
                confidence=s.confidence,
                trend=s.trend,
                reasons=s.get_reasons(),
                indicators_passed=s.get_indicators_passed(),
                smc_confirmation=s.get_smc_confirmation(),
                estimated_win_rate=s.estimated_win_rate,
                trade_duration=s.trade_duration,
                is_active=s.is_active,
                result=s.result,
                profit_loss=s.profit_loss,
                created_at=s.created_at.isoformat() if s.created_at else None,
                closed_at=s.closed_at.isoformat() if s.closed_at else None,
            )
            for s in signals
        ]

        return SignalListResponse(
            total=len(signal_list),
            signals=signal_list,
            timestamp=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        logger.error(f"Error getting signals for pair {pair}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/signals/stats/overview",
    response_model=SignalStatsResponse,
    summary="Get signal statistics",
)
async def get_signal_stats(
    authorized: bool = Depends(verify_api_key),
):
    try:
        async with AsyncSessionLocal() as db:
            signals_today = await SignalCRUD.count_today(db)
            win_rate = await SignalCRUD.get_win_rate(db)
            active_signals = await SignalCRUD.get_active(db)
            all_signals = await SignalCRUD.get_recent(db, limit=1000)

        return SignalStatsResponse(
            total_signals=len(all_signals),
            signals_today=signals_today,
            win_rate=round(win_rate, 2),
            active_signals=len(active_signals),
            timestamp=datetime.utcnow().isoformat(),
        )
    except Exception as e:
        logger.error(f"Error getting signal stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


__all__ = ["router"]

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.instrument import Instrument
from app.models.candle import Candle
from app.schemas.candle import CandleRead
from app.services.session import SessionEngine, CurrentSessionState

router = APIRouter(prefix="/sessions", tags=["Trading Sessions"])

@router.get("/current", response_model=CurrentSessionState)
async def get_current_session():
    """
    Returns real-time session status, active sessions, overlaps, and IANA timezone windows.
    """
    now_utc = datetime.now(timezone.utc)
    return SessionEngine.evaluate_sessions(dt_utc=now_utc)

@router.get("/evaluate", response_model=CurrentSessionState)
async def evaluate_session_at_timestamp(
    timestamp_utc: datetime = Query(..., description="UTC timestamp to evaluate (ISO format)")
):
    """
    Evaluates session status, active sessions, and overlaps for any given historical or future UTC timestamp.
    """
    return SessionEngine.evaluate_sessions(dt_utc=timestamp_utc)

@router.get("/levels/{symbol}", response_model=CurrentSessionState)
async def get_session_levels_for_symbol(
    symbol: str,
    timeframe: str = Query("15m", description="Intraday timeframe to fetch session candles"),
    db: AsyncSession = Depends(get_db),
):
    """
    Computes Asian, London, and New York session high/low/range levels
    and sweeps for the specified instrument using candles from the current day.
    """
    # 1. Fetch instrument
    inst_res = await db.execute(select(Instrument).where(Instrument.symbol == symbol.upper()))
    instrument = inst_res.scalar_one_or_none()
    if not instrument:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instrument '{symbol}' not found."
        )

    # 2. Get start of today in UTC
    now_utc = datetime.now(timezone.utc)
    start_of_day = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)

    # 3. Query candles for today
    stmt = (
        select(Candle)
        .where(
            Candle.instrument_id == instrument.id,
            Candle.timeframe == timeframe,
            Candle.timestamp_utc >= start_of_day,
        )
        .order_by(Candle.timestamp_utc.asc())
    )
    res = await db.execute(stmt)
    db_candles = res.scalars().all()
    candles_read = [CandleRead.model_validate(c) for c in db_candles]

    pip_size = float(instrument.pip_size) if instrument.pip_size else 0.0001
    return SessionEngine.evaluate_sessions(
        dt_utc=now_utc,
        candles_today=candles_read,
        pip_size=pip_size,
    )

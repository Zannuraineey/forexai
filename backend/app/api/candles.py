from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.schemas.candle import CandleRead, GapReport
from app.services.candle_service import CandleService
from app.services.market_data import get_market_data_provider, GapRecoveryEngine

router = APIRouter(prefix="/candles", tags=["Candles"])

@router.get("/summary/watchlist")
async def get_watchlist_summary(
    db: AsyncSession = Depends(get_db)
) -> List[dict]:
    """
    Returns concise market overview for all active watchlist instruments:
    symbol, last_price, change_pct, session, and market_status.
    """
    from app.models.instrument import Instrument
    from app.services.session.session_engine import SessionEngine
    from sqlalchemy import select

    stmt = select(Instrument).where(Instrument.is_active == True).order_by(Instrument.symbol)
    result = await db.execute(stmt)
    instruments = result.scalars().all()

    current_session = SessionEngine.evaluate_sessions(datetime.now(timezone.utc))
    primary_session = (
        current_session.primary_session.capitalize()
        if current_session.primary_session
        else ("Overlap" if current_session.is_overlap else "Off-Session")
    )

    svc = CandleService(db)
    summary = []

    now_utc = datetime.now(timezone.utc)
    is_weekend = now_utc.weekday() >= 5 or (now_utc.weekday() == 6 and now_utc.hour < 21)

    for inst in instruments:
        # Fast in-memory/DB read without triggering blocking WebSocket connections
        candles = await svc.get_candles(symbol=inst.symbol, timeframe="1m", limit=2, auto_fetch=False)
        if not candles:
            candles = await svc.get_candles(symbol=inst.symbol, timeframe="15m", limit=2, auto_fetch=False)

        is_stale = False
        if candles:
            c_ts = candles[-1].timestamp_utc
            if c_ts.tzinfo is None:
                c_ts = c_ts.replace(tzinfo=timezone.utc)
            is_synth = any(k in inst.symbol.upper() for k in ["BOOM", "CRASH", "R_", "1HZ", "RB", "WLD", "JD", "STP", "DEX"])
            if (is_synth or not is_weekend) and (now_utc - c_ts).total_seconds() > 300:
                is_stale = True

        # If missing or stale, fetch on-demand to provide live market prices
        if not candles or is_stale:
            try:
                candles = await svc.get_candles(symbol=inst.symbol, timeframe="1m", limit=2, auto_fetch=True)
            except Exception:
                pass


        price = None
        change_pct = 0.0

        if candles:
            latest = candles[-1]
            price = latest.close
            prev = candles[0] if len(candles) > 1 else latest
            if prev.open > 0:
                change_pct = round(((latest.close - prev.open) / prev.open) * 100, 2)

        is_synthetic = any(k in inst.symbol.upper() for k in ["BOOM", "CRASH", "R_", "1HZ", "RB", "WLD", "JD", "STP", "DEX"])
        market_status = "Open" if (is_synthetic or not is_weekend) else "Closed"

        summary.append({
            "symbol": inst.symbol,
            "base_asset": inst.base_asset,
            "quote_asset": inst.quote_asset,
            "price": price,
            "change_pct": change_pct,
            "session": primary_session,
            "market_status": market_status,
            "pip_size": float(inst.pip_size),
        })

    return summary

@router.get("/{symbol}", response_model=List[CandleRead])
async def get_candles(
    symbol: str,
    timeframe: str = Query("15m", description="Candle timeframe e.g. 1m, 5m, 15m, 1h, 4h, 1d"),
    start_utc: Optional[datetime] = Query(None, description="Start timestamp (UTC)"),
    end_utc: Optional[datetime] = Query(None, description="End timestamp (UTC)"),
    limit: int = Query(500, le=2000, description="Max candles to return"),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve historical/live OHLCV candles for a given instrument and timeframe."""
    if timeframe not in settings.TARGET_TIMEFRAMES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid timeframe: '{timeframe}'. Allowed: {settings.TARGET_TIMEFRAMES}"
        )
    
    svc = CandleService(db)
    candles = await svc.get_candles(
        symbol=symbol.upper(),
        timeframe=timeframe,
        start_utc=start_utc,
        end_utc=end_utc,
        limit=limit
    )
    return candles

@router.post("/recover-gaps", response_model=List[GapReport])
async def trigger_gap_recovery(
    symbol: Optional[str] = Query(None, description="Specific symbol or all if omitted"),
    timeframe: Optional[str] = Query(None, description="Specific timeframe or all if omitted"),
    provider_name: str = Query("deriv", description="Market data provider name"),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually triggers gap recovery check and backfill for missing candle intervals.
    """
    provider = get_market_data_provider(provider_name)
    engine = GapRecoveryEngine(db, provider)
    
    symbols = [symbol.upper()] if symbol else settings.TARGET_INSTRUMENTS
    timeframes = [timeframe] if timeframe else settings.TARGET_TIMEFRAMES

    reports = await engine.recover_all(symbols=symbols, timeframes=timeframes)
    return reports

from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.schemas.candle import CandleRead
from app.services.candle_service import CandleService
from app.services.features.context_engine import MarketContextEngine, MarketContextSnapshot

router = APIRouter(prefix="/context", tags=["Market Context"])

@router.get("/{symbol}", response_model=MarketContextSnapshot)
async def get_market_context(
    symbol: str,
    timeframe: str = Query("15m", description="Trigger timeframe (e.g. 1m, 5m, 15m, 1h, 4h, 1d)"),
    lookback: int = Query(100, ge=15, le=500, description="Bars of context for indicators and structure"),
    db: AsyncSession = Depends(get_db)
):
    """
    Computes and exposes neutral, objective market context for a given symbol:
    - ATR, RSI, EMA suite (9, 21, 50, 200), MACD, ADX
    - Candle structure (body, wicks, pin-bar, engulfing)
    - Market structure (Fractal swing highs/lows, HH/HL/LH/LL labeling, active FVGs)
    - Key reference levels (PDH, PDL, PWH, PWL, ADR)
    - Liquidity sweeps
    """
    symbol_clean = symbol.upper()
    svc = CandleService(db)
    inst = await svc.ensure_instrument(symbol_clean)

    # 1. Fetch trigger timeframe candles
    candles = await svc.get_candles(symbol=symbol_clean, timeframe=timeframe, limit=lookback)
    if len(candles) < 15:
        raise HTTPException(
            status_code=404,
            detail=f"Insufficient candle history for {symbol_clean} ({timeframe}). Found {len(candles)} bars; at least 15 required."
        )

    # 2. Fetch daily candles for PDH/PDL and reference levels
    daily_candles = await svc.get_candles(symbol=symbol_clean, timeframe="1d", limit=30)

    # 3. Generate context snapshot
    snapshot = MarketContextEngine.generate_context(
        symbol=symbol_clean,
        timeframe=timeframe,
        candles=candles,
        daily_candles=daily_candles,
        pip_size=float(inst.pip_size),
    )

    return snapshot

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.msnr import (
    MSNRAnalysisResult,
    MSNRZone,
    MSNRSetupSignal,
)
from app.services.candle_service import CandleService
from app.services.features.msnr_engine import MSNREngine
from app.services.features.smt_engine import SMTEngine

router = APIRouter(prefix="/msnr", tags=["MSNR & Alchemist Playbook"])


@router.get("/analysis", response_model=MSNRAnalysisResult)
async def get_msnr_analysis(
    symbol: str = Query("XAUUSD", description="Symbol to evaluate (e.g. XAUUSD, XAGUSD, EURUSD, GBPUSD)"),
    timeframe: str = Query("15m", description="Timeframe for MSNR analysis"),
    limit: int = Query(60, ge=20, le=300, description="Number of candles to evaluate"),
    db: AsyncSession = Depends(get_db),
):
    """
    Evaluates Malaysian Support & Resistance (MSNR) and Alchemist Playbook setups.
    Includes Classic A / Classic V, RBS / SBR flip zones, 50% Consequent Encroachment (CE),
    and Daily Profile #2 NY Reversals cross-referenced with correlated SMT Divergence.
    """
    candle_svc = CandleService(db)
    candles = await candle_svc.get_candles(symbol.upper(), timeframe=timeframe, limit=limit, auto_fetch=False)

    # Fetch intermarket SMT divergence for correlated pairs
    smt_ctx = await SMTEngine.evaluate_smt_for_symbol(
        symbol=symbol.upper(),
        db=db,
        timeframe=timeframe,
    )

    pip_size = 0.01 if "XAU" in symbol.upper() or "XAG" in symbol.upper() else 0.0001

    return MSNREngine.analyze(
        symbol=symbol.upper(),
        candles=candles,
        smt_divergence=smt_ctx.active_divergence,
        pip_size=pip_size,
    )


@router.get("/zones", response_model=List[MSNRZone])
async def get_msnr_zones(
    symbol: str = Query("XAUUSD", description="Symbol to evaluate"),
    timeframe: str = Query("15m", description="Timeframe"),
    limit: int = Query(60, ge=20, le=300),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns active MSNR key zones (Classic A, Classic V, RBS, SBR) with 50% CE levels and freshness ratings.
    """
    candle_svc = CandleService(db)
    candles = await candle_svc.get_candles(symbol.upper(), timeframe=timeframe, limit=limit, auto_fetch=False)
    pip_size = 0.01 if "XAU" in symbol.upper() or "XAG" in symbol.upper() else 0.0001
    zones = MSNREngine.identify_msnr_zones(candles, pip_size=pip_size)
    return [z for z in zones if z.is_active]


@router.get("/setups", response_model=List[MSNRSetupSignal])
async def get_msnr_setups(
    symbol: str = Query("XAUUSD", description="Symbol to evaluate"),
    timeframe: str = Query("15m", description="Timeframe"),
    limit: int = Query(60, ge=20, le=300),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns high-probability MSNR & SMT Alchemist setups currently actionable or pending.
    """
    analysis = await get_msnr_analysis(symbol=symbol, timeframe=timeframe, limit=limit, db=db)
    return analysis.signals

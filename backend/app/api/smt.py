from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas import SMTContext, SMTDivergenceDetail, SMTPairGroup
from app.services.features import SMTEngine

router = APIRouter(prefix="/smt", tags=["SMT Divergence Engine"])

@router.get("/divergence", response_model=SMTContext)
async def get_smt_divergence(
    symbol: str = Query("XAUUSD", description="Symbol to evaluate (e.g. XAUUSD, XAGUSD, EURUSD, GBPUSD)"),
    timeframe: str = Query("15m", description="Timeframe for divergence comparison"),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns real-time SMT divergence analysis for a target instrument against its correlated partner.
    Supported pairs:
    - Precious Metals: XAUUSD vs XAGUSD
    - Majors: EURUSD vs GBPUSD
    """
    return await SMTEngine.evaluate_smt_for_symbol(
        symbol=symbol,
        db=db,
        timeframe=timeframe,
    )

@router.get("/matrix", response_model=List[SMTContext])
async def get_smt_matrix(
    timeframe: str = Query("15m", description="Timeframe for divergence comparison"),
    db: AsyncSession = Depends(get_db),
):
    """
    Evaluates all tracked correlated asset groups and returns an SMT matrix.
    """
    monitored_primary_symbols = ["XAUUSD", "EURUSD"]
    results = []
    for sym in monitored_primary_symbols:
        ctx = await SMTEngine.evaluate_smt_for_symbol(
            symbol=sym,
            db=db,
            timeframe=timeframe,
        )
        results.append(ctx)
    return results

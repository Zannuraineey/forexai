from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db
from app.models.trade_outcome import TradeSetupOutcome
from app.schemas.quant_research import (
    QuantResearchReport,
    CohortEdgeResult,
    CandidateEdgeEvaluationRequest,
)
from app.services.quant.quant_research_engine import QuantResearchEngine

router = APIRouter(prefix="/quant", tags=["Quantitative Research"])


@router.get("/research", response_model=QuantResearchReport)
async def get_quant_research_report(
    symbol: Optional[str] = Query(None, description="Filter by instrument symbol (e.g. EURUSD, XAGUSD)"),
    min_sample: int = Query(30, ge=5, le=500, description="Minimum sample size required to validate statistical edge"),
    db: AsyncSession = Depends(get_db),
):
    """
    Computes empirical statistical edge across all multivariate cohorts:
    (7H Profile × Session × DXY Alignment × Liquidity Sweep × MSS).
    Identifies PROVEN_EDGE cohorts (high expectancy, p < 0.05) and NEGATIVE_EDGE veto regimes.
    """
    return await QuantResearchEngine.load_and_analyze_from_db(
        db=db,
        symbol=symbol,
        min_sample_size=min_sample,
    )


@router.post("/evaluate-candidate", response_model=CohortEdgeResult)
async def evaluate_candidate_edge(
    req: CandidateEdgeEvaluationRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Evaluates an incoming candidate setup snapshot against accumulated database trade outcomes.
    Returns matching cohort expectancy, win rate, milestone decay curve, and recommended grade/veto.
    """
    # Fetch all historical outcomes for the symbol
    stmt = (
        select(TradeSetupOutcome)
        .where(TradeSetupOutcome.symbol == req.symbol.upper())
        .order_by(desc(TradeSetupOutcome.signal_timestamp_utc))
    )
    res = await db.execute(stmt)
    historical_outcomes = list(res.scalars().all())

    return QuantResearchEngine.evaluate_candidate_edge(
        candidate_symbol=req.symbol.upper(),
        candidate_direction=req.direction.upper(),
        candidate_snapshot=req.setup_snapshot,
        historical_setups=historical_outcomes,
        min_sample_size=req.min_sample_size,
    )

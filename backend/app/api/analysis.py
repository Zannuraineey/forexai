from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db
from app.models.analysis import AnalysisResult, AnalysisStateEnum
from app.models.instrument import Instrument
from app.schemas.ai_analysis import (
    AIAnalysisRequest,
    AnalysisRecordRead,
    ConditionStatus,
    AmbiguityItem,
)
from app.services.ai import AIAnalysisEngine

router = APIRouter(prefix="/analysis", tags=["AI Market Analysis"])

@router.post("/evaluate", response_model=AnalysisRecordRead)
async def evaluate_market(
    request: AIAnalysisRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Executes AI analysis for the specified instrument, timeframe, and session instructions.
    Persists the traceable result to PostgreSQL.
    """
    engine = AIAnalysisEngine(db)
    try:
        return await engine.execute_analysis(request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/history", response_model=List[AnalysisRecordRead])
async def get_analysis_history(
    symbol: Optional[str] = Query(None, description="Filter by instrument symbol (e.g. EURUSD)"),
    timeframe: Optional[str] = Query(None, description="Filter by timeframe (e.g. 15m)"),
    session_name: Optional[str] = Query(None, description="Filter by session (asian, london, new_york)"),
    state: Optional[AnalysisStateEnum] = Query(None, description="Filter by analysis state"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    Queries past AI analysis results with full traceability to symbol, timeframe,
    timestamp, session, instruction version, and model.
    """
    stmt = select(AnalysisResult, Instrument.symbol).join(
        Instrument, AnalysisResult.instrument_id == Instrument.id
    )

    if symbol:
        stmt = stmt.where(Instrument.symbol == symbol.upper())
    if timeframe:
        stmt = stmt.where(AnalysisResult.timeframe == timeframe)
    if session_name:
        stmt = stmt.where(AnalysisResult.session_name == session_name.lower())
    if state:
        stmt = stmt.where(AnalysisResult.state == state.value)

    stmt = stmt.order_by(desc(AnalysisResult.timestamp_utc)).offset(offset).limit(limit)
    res = await db.execute(stmt)
    rows = res.all()

    output = []
    for record, sym in rows:
        cb = [ConditionStatus(**c) if isinstance(c, dict) else c for c in (record.condition_breakdown or [])]
        amb = [AmbiguityItem(**a) if isinstance(a, dict) else a for a in (record.ambiguities_detected or [])]

        output.append(
            AnalysisRecordRead(
                id=record.id,
                symbol=sym,
                instrument_id=record.instrument_id,
                candle_id=record.candle_id,
                timeframe=record.timeframe,
                timestamp_utc=record.timestamp_utc,
                session_name=record.session_name,
                instruction_version_id=record.instruction_version_id,
                instruction_version_number=None,
                model_version=record.model_version,
                state=AnalysisStateEnum(record.state),
                summary=record.summary,
                condition_breakdown=cb,
                ambiguities_detected=amb,
                full_reasoning=record.full_reasoning,
                created_at=record.created_at,
            )
        )

    return output

@router.get("/scanner/status")
async def get_scanner_status():
    """
    Returns the real-time background session scanner health and statistics.
    """
    from app.services.ai import get_session_scanner
    return get_session_scanner().get_status()

@router.post("/scanner/run-once")
async def trigger_scanner_run():
    """
    Manually triggers an immediate scan cycle across active watchlist instruments.
    """
    from app.services.ai import get_session_scanner
    return await get_session_scanner().scan_cycle()

@router.get("/{analysis_id}", response_model=AnalysisRecordRead)
async def get_analysis_by_id(
    analysis_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves a single analysis result by ID.
    """
    stmt = (
        select(AnalysisResult, Instrument.symbol)
        .join(Instrument, AnalysisResult.instrument_id == Instrument.id)
        .where(AnalysisResult.id == analysis_id)
    )
    res = await db.execute(stmt)
    row = res.first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis record {analysis_id} not found."
        )

    record, sym = row
    cb = [ConditionStatus(**c) if isinstance(c, dict) else c for c in (record.condition_breakdown or [])]
    amb = [AmbiguityItem(**a) if isinstance(a, dict) else a for a in (record.ambiguities_detected or [])]

    return AnalysisRecordRead(
        id=record.id,
        symbol=sym,
        instrument_id=record.instrument_id,
        candle_id=record.candle_id,
        timeframe=record.timeframe,
        timestamp_utc=record.timestamp_utc,
        session_name=record.session_name,
        instruction_version_id=record.instruction_version_id,
        instruction_version_number=None,
        model_version=record.model_version,
        state=AnalysisStateEnum(record.state),
        summary=record.summary,
        condition_breakdown=cb,
        ambiguities_detected=amb,
        full_reasoning=record.full_reasoning,
        created_at=record.created_at,
    )

from app.schemas.backtest import BacktestRequest, BacktestResultRead
from app.services.backtesting import BacktestEngine
from app.models.analysis import Backtest

@router.post("/backtest", response_model=BacktestResultRead)
async def run_strategy_backtest(
    request: BacktestRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Executes a historical backtest for the specified instrument, timeframe, session,
    and instruction set across the requested date span.
    """
    engine = BacktestEngine(db)
    try:
        return await engine.run_backtest(request, user_id=1)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/backtest/{backtest_id}", response_model=BacktestResultRead)
async def get_backtest_by_id(
    backtest_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves results and setup distribution of a prior backtest.
    """
    stmt = (
        select(Backtest, Instrument.symbol)
        .join(Instrument, Backtest.instrument_id == Instrument.id)
        .where(Backtest.id == backtest_id)
    )
    res = await db.execute(stmt)
    row = res.first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backtest record {backtest_id} not found."
        )

    bt, sym = row
    return BacktestResultRead(
        id=bt.id,
        symbol=sym,
        instrument_id=bt.instrument_id,
        timeframe=bt.timeframe,
        session_name=bt.session_name,
        instruction_version_id=bt.instruction_version_id,
        start_date=bt.start_date,
        end_date=bt.end_date,
        total_candles_analyzed=bt.total_candles_analyzed,
        state_distribution=bt.state_distribution or {},
        identified_setups=bt.identified_setups or [],
        status=bt.status,
        created_at=bt.created_at,
    )

@router.get("/ut-bot/{symbol}")
async def get_ut_bot_analysis(
    symbol: str,
    timeframe: str = Query(default="15m"),
    sensitivity: Optional[float] = Query(default=None),
    atr_period: int = Query(default=10),
    db: AsyncSession = Depends(get_db),
):
    """
    Computes real-time non-repainting UT Bot analysis, trailing stop,
    EMA 200 trend, and RSI momentum for the specified symbol.
    Optimized for Deriv Volatility 75 (R_75) and cross-pair monitoring.
    """
    from app.services.ai.ut_bot import UTBotEngine
    from app.models.candle import Candle
    from app.schemas.candle import CandleRead

    sym = symbol.upper()
    inst_res = await db.execute(select(Instrument).where(Instrument.symbol == sym))
    instrument = inst_res.scalar_one_or_none()
    if not instrument:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instrument '{sym}' not found in active instruments. Toggle it in the Markets catalog first."
        )

    # Determine default sensitivity: 1.5 for Deriv Volatility indices, 1.2 for Forex
    if sensitivity is None:
        if "R_" in sym or "VOLATILITY" in sym or "1HZ" in sym or "BOOM" in sym or "CRASH" in sym:
            sens = 1.5
        else:
            sens = 1.2
    else:
        sens = sensitivity

    # Fetch candles for requested timeframe
    stmt = (
        select(Candle)
        .where(Candle.instrument_id == instrument.id, Candle.timeframe == timeframe)
        .order_by(desc(Candle.timestamp_utc))
        .limit(100)
    )
    c_res = await db.execute(stmt)
    candles = [CandleRead.model_validate(c) for c in reversed(c_res.scalars().all())]

    result = UTBotEngine.evaluate(
        candles=candles,
        sensitivity=sens,
        atr_period=atr_period,
        symbol=sym,
        timeframe=timeframe,
    )
    result["symbol"] = sym
    result["timeframe"] = timeframe

    # Compute MTF signals
    mtf = {}
    for tf in ["5m", "15m", "1h"]:
        if tf == timeframe:
            mtf[tf] = result["signal"]
        else:
            tf_stmt = (
                select(Candle)
                .where(Candle.instrument_id == instrument.id, Candle.timeframe == tf)
                .order_by(desc(Candle.timestamp_utc))
                .limit(60)
            )
            tf_res = await db.execute(tf_stmt)
            tf_candles = [CandleRead.model_validate(c) for c in reversed(tf_res.scalars().all())]
            if tf_candles:
                tf_eval = UTBotEngine.evaluate(
                    tf_candles,
                    sensitivity=sens,
                    atr_period=atr_period,
                    symbol=sym,
                    timeframe=tf,
                )
                mtf[tf] = tf_eval["signal"]
            else:
                mtf[tf] = "WAIT"
    result["mtf"] = mtf

    return result

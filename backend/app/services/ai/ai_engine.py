from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.core.logging import logger

from app.models.instrument import Instrument
from app.models.candle import Candle
from app.models.analysis import AnalysisResult, AnalysisStateEnum
from app.models.strategy import InstructionVersion
from app.schemas.candle import CandleRead
from app.schemas.ai_analysis import (
    AIAnalysisRequest,
    AIAnalysisOutput,
    AnalysisRecordRead,
    ConditionStatus,
    AmbiguityItem,
    TradeSetup,
)
from app.services.features.context_engine import MarketContextEngine, MarketContextSnapshot
from app.services.session import SessionEngine
from app.services.strategy_service import StrategyService
from app.services.context.market_context_assembler import MarketContextAssembler
from app.services.ai.provider_interface import IAIAnalysisProvider
from app.services.ai.deterministic_provider import DeterministicAIProvider
from app.services.news.dxy_service import DXYService
from app.services.news.economic_calendar_service import EconomicCalendarService
from app.services.tracking.outcome_tracker import TradeOutcomeTracker

class AIAnalysisEngine:
    """
    Core AI Analysis Orchestrator.
    Adheres strictly to the unidirectional pipeline:
    USER INSTRUCTIONS -> MARKET DATA -> MARKET CONTEXT -> AI ANALYSIS -> TRACEABLE RECORD

    Assembles market data, technical features, session state, and user's session instructions,
    then executes reasoning without hardcoded strategy assumptions.
    """

    def __init__(self, db: AsyncSession, provider: Optional[IAIAnalysisProvider] = None):
        self.db = db
        self.provider = provider or DeterministicAIProvider()

    async def execute_analysis(
        self,
        request: AIAnalysisRequest,
        model_version: str = "deterministic-v1",
    ) -> AnalysisRecordRead:
        symbol = request.symbol.upper()
        timeframe = request.timeframe

        # 1. Fetch Instrument
        inst_res = await self.db.execute(select(Instrument).where(Instrument.symbol == symbol))
        instrument = inst_res.scalar_one_or_none()
        if not instrument:
            raise ValueError(f"Instrument '{symbol}' not found in database.")

        # 2. Fetch Recent Candles for Market Context
        stmt = (
            select(Candle)
            .where(Candle.instrument_id == instrument.id, Candle.timeframe == timeframe)
            .order_by(desc(Candle.timestamp_utc))
            .limit(60)
        )
        c_res = await self.db.execute(stmt)
        candles_raw = c_res.scalars().all()
        if not candles_raw:
            raise ValueError(f"No candle data available for '{symbol}' on timeframe '{timeframe}'.")

        # Ascending order
        candles = [CandleRead.model_validate(c) for c in reversed(candles_raw)]
        current_candle = candles[-1]

        # Fetch daily candles for PDH/PDL and reference levels (no look-ahead)
        d_stmt = (
            select(Candle)
            .where(
                Candle.instrument_id == instrument.id,
                Candle.timeframe == "1d",
                Candle.timestamp_utc <= current_candle.timestamp_utc,
            )
            .order_by(desc(Candle.timestamp_utc))
            .limit(30)
        )
        d_res = await self.db.execute(d_stmt)
        daily_candles = [CandleRead.model_validate(c) for c in reversed(d_res.scalars().all())]

        pip_size = float(instrument.pip_size) if instrument.pip_size else 0.0001

        # 3. Generate Complete Market Context Snapshot
        context_snapshot: MarketContextSnapshot = MarketContextEngine.generate_context(
            symbol=symbol,
            timeframe=timeframe,
            candles=candles,
            daily_candles=daily_candles,
            pip_size=pip_size,
        )

        # 3b. Multi-Timeframe Context & 7H Profile Assembly (strictly aligned to setup timestamp)
        async def _fetch_tf_candles(tf: str) -> List[CandleRead]:
            if tf == timeframe:
                return candles
            q = (
                select(Candle)
                .where(
                    Candle.instrument_id == instrument.id,
                    Candle.timeframe == tf,
                    Candle.timestamp_utc <= current_candle.timestamp_utc,
                )
                .order_by(desc(Candle.timestamp_utc))
                .limit(60)
            )
            q_res = await self.db.execute(q)
            q_raw = q_res.scalars().all()
            return [CandleRead.model_validate(c) for c in reversed(q_raw)]

        candles_4h = await _fetch_tf_candles("4h")
        candles_1h = await _fetch_tf_candles("1h")
        candles_15m = await _fetch_tf_candles("15m")

        candles_by_tf = {
            "4h": candles_4h,
            "1h": candles_1h,
            "15m": candles_15m,
            timeframe: candles,
        }

        # 3c. Real, timestamp-aligned DXY and Macro News Intelligence
        dxy_svc = DXYService(self.db)
        dxy_metrics = await dxy_svc.calculate_dxy_index(as_of_timestamp=current_candle.timestamp_utc)
        if dxy_metrics:
            dxy_data = {
                "direction": dxy_metrics.trend,
                "trend": dxy_metrics.trend,
                "trend_strength": dxy_metrics.confirmation_status,
                "change": dxy_metrics.change_pct,
                "change_pct": dxy_metrics.change_pct,
                "value": dxy_metrics.value,
                "source": dxy_metrics.source,
            }
        else:
            dxy_data = {
                "dxy_direction": "UNAVAILABLE",
                "dxy_trend_strength": None,
                "dxy_change": None,
                "dxy_relationship_to_symbol": "UNAVAILABLE",
            }

        cal_svc = EconomicCalendarService()
        news_data = cal_svc.get_news_risk_at(
            symbol=symbol,
            timestamp_utc=current_candle.timestamp_utc,
            window_minutes=60,
        )

        from app.services.features.msnr_engine import MSNREngine
        from app.services.features.smt_engine import SMTEngine

        smt_ctx = await SMTEngine.evaluate_smt_for_symbol(
            symbol=symbol,
            db=self.db,
            timeframe=timeframe,
            session_levels=context_snapshot.session_state.session_levels if context_snapshot.session_state else None,
        )
        msnr_analysis = MSNREngine.analyze(
            symbol=symbol,
            candles=candles,
            smt_divergence=smt_ctx.active_divergence,
            pip_size=pip_size,
        )
        msnr_data = msnr_analysis.model_dump()
        smt_data = smt_ctx.model_dump()

        structured_state = MarketContextAssembler.assemble(
            symbol=symbol,
            requested_timeframe=timeframe,
            current_candle=current_candle,
            candles_by_timeframe=candles_by_tf,
            session_state=context_snapshot.session_state,
            market_structure=context_snapshot.market_structure,
            reference_levels=context_snapshot.reference_levels,
            recent_liquidity_sweeps=context_snapshot.recent_liquidity_sweeps,
            dxy_data=dxy_data,
            news_data=news_data,
            smt_data=smt_data,
            msnr_data=msnr_data,
        )
        context_snapshot.structured_market_state = structured_state
        context_snapshot.dxy = dxy_data
        context_snapshot.news = news_data

        # 4. Resolve Active Session
        session_name = request.session_name
        if not session_name:
            curr_state = SessionEngine.evaluate_sessions(current_candle.timestamp_utc)
            session_name = curr_state.primary_session or "asian"
        session_name = session_name.lower()

        # 5. Fetch Session Strategy Instructions & Exact Version
        strat_svc = StrategyService(self.db)
        instruction_version_id: Optional[int] = None
        instruction_version_number: Optional[int] = None
        user_instructions_text = ""

        if request.custom_instructions:
            user_instructions_text = request.custom_instructions
        elif request.instruction_version_id:
            stmt_v = select(InstructionVersion).where(InstructionVersion.id == request.instruction_version_id)
            v_res = await self.db.execute(stmt_v)
            iv = v_res.scalar_one_or_none()
            if iv:
                instruction_version_id = iv.id
                instruction_version_number = iv.version
                user_instructions_text = iv.prompt_content
        else:
            inst = await strat_svc.get_or_create_instruction(user_id=1, session_name=session_name)
            active_ver = await strat_svc.get_active_version(inst.id, inst.current_version)
            if active_ver:
                instruction_version_id = active_ver.id
                instruction_version_number = active_ver.version
                user_instructions_text = active_ver.prompt_content

        # 6. Fetch Relevant Previous Analysis
        prev_stmt = (
            select(AnalysisResult)
            .where(
                AnalysisResult.instrument_id == instrument.id,
                AnalysisResult.timeframe == timeframe,
            )
            .order_by(desc(AnalysisResult.timestamp_utc))
            .limit(1)
        )
        prev_res = await self.db.execute(prev_stmt)
        prev_record = prev_res.scalar_one_or_none()
        previous_analysis_dict = None
        if prev_record:
            previous_analysis_dict = {
                "state": prev_record.state,
                "timestamp_utc": prev_record.timestamp_utc.isoformat(),
                "summary": prev_record.summary,
            }

        # 7. Execute AI Evaluation
        ai_output: AIAnalysisOutput = await self.provider.analyze(
            market_context=context_snapshot.model_dump(),
            user_instructions=user_instructions_text,
            previous_analysis=previous_analysis_dict,
        )

        # 8. Persist Analysis Result to PostgreSQL
        # Check if record already exists for (instrument_id, timeframe, timestamp_utc, instruction_version_id)
        existing_stmt = select(AnalysisResult).where(
            AnalysisResult.instrument_id == instrument.id,
            AnalysisResult.timeframe == timeframe,
            AnalysisResult.timestamp_utc == current_candle.timestamp_utc,
            AnalysisResult.instruction_version_id == instruction_version_id,
        )
        existing_res = await self.db.execute(existing_stmt)
        record = existing_res.scalar_one_or_none()

        cond_dump = [c.model_dump() for c in ai_output.condition_breakdown]
        amb_dump = [a.model_dump() for a in ai_output.ambiguities_detected]
        setup_dump = ai_output.trade_setup.model_dump() if ai_output.trade_setup else None

        if not record:
            record = AnalysisResult(
                instrument_id=instrument.id,
                candle_id=current_candle.id,
                timeframe=timeframe,
                timestamp_utc=current_candle.timestamp_utc,
                session_name=session_name,
                instruction_version_id=instruction_version_id,
                model_version=model_version,
                state=ai_output.state.value,
                summary=ai_output.summary,
                condition_breakdown=cond_dump,
                ambiguities_detected=amb_dump,
                full_reasoning=ai_output.full_reasoning,
                trade_setup=setup_dump,
                created_at=datetime.now(timezone.utc),
            )
            self.db.add(record)
        else:
            record.state = ai_output.state.value
            record.summary = ai_output.summary
            record.condition_breakdown = cond_dump
            record.ambiguities_detected = amb_dump
            record.full_reasoning = ai_output.full_reasoning
            record.trade_setup = setup_dump
            record.model_version = model_version

        await self.db.commit()
        await self.db.refresh(record)

        # 9. Persist Candidate Setup in TradeOutcomeTracker if VALID_SETUP
        if ai_output.trade_setup and ai_output.state == AnalysisStateEnum.VALID_SETUP:
            ts_unix = int(current_candle.timestamp_utc.timestamp())
            cand_setup_id = f"setup_{symbol}_{timeframe}_{ts_unix}"
            ts_snapshot_dict = {}
            if ai_output.setup_snapshot:
                ts_snapshot_dict = ai_output.setup_snapshot.model_dump()
            elif ai_output.trade_setup.setup_snapshot:
                ts_snapshot_dict = ai_output.trade_setup.setup_snapshot.model_dump()
            try:
                await TradeOutcomeTracker.persist_candidate_setup(
                    db_session=self.db,
                    setup_id=cand_setup_id,
                    symbol=symbol,
                    direction=ai_output.trade_setup.action,
                    entry_price=ai_output.trade_setup.entry_price,
                    stop_loss=ai_output.trade_setup.stop_loss,
                    take_profit=ai_output.trade_setup.take_profit,
                    signal_timestamp_utc=current_candle.timestamp_utc,
                    setup_snapshot=ts_snapshot_dict,
                )
            except Exception as e:
                logger.warning(f"Could not persist candidate trade setup outcome: {e}")

        return AnalysisRecordRead(
            id=record.id,
            symbol=symbol,
            instrument_id=instrument.id,
            candle_id=record.candle_id,
            timeframe=record.timeframe,
            timestamp_utc=record.timestamp_utc,
            session_name=record.session_name,
            instruction_version_id=record.instruction_version_id,
            instruction_version_number=instruction_version_number,
            model_version=record.model_version,
            state=AnalysisStateEnum(record.state),
            summary=record.summary,
            condition_breakdown=ai_output.condition_breakdown,
            ambiguities_detected=ai_output.ambiguities_detected,
            full_reasoning=record.full_reasoning,
            trade_setup=ai_output.trade_setup,
            setup_snapshot=ai_output.setup_snapshot,
            bias_validation=ai_output.bias_validation,
            created_at=record.created_at,
        )

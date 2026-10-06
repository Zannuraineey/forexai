from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

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
)
from app.services.features.context_engine import MarketContextEngine, MarketContextSnapshot
from app.services.session import SessionEngine
from app.services.strategy_service import StrategyService
from app.services.ai.provider_interface import IAIAnalysisProvider
from app.services.ai.deterministic_provider import DeterministicAIProvider

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

        # Fetch daily candles for PDH/PDL and reference levels
        d_stmt = (
            select(Candle)
            .where(Candle.instrument_id == instrument.id, Candle.timeframe == "1d")
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
                created_at=datetime.now(timezone.utc),
            )
            self.db.add(record)
        else:
            record.state = ai_output.state.value
            record.summary = ai_output.summary
            record.condition_breakdown = cond_dump
            record.ambiguities_detected = amb_dump
            record.full_reasoning = ai_output.full_reasoning
            record.model_version = model_version

        await self.db.commit()
        await self.db.refresh(record)

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
            created_at=record.created_at,
        )

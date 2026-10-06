from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from collections import defaultdict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.instrument import Instrument
from app.models.candle import Candle
from app.models.analysis import Backtest, AnalysisStateEnum
from app.schemas.candle import CandleRead
from app.schemas.backtest import BacktestRequest, BacktestResultRead
from app.services.features.context_engine import MarketContextEngine
from app.services.session import SessionEngine
from app.services.strategy_service import StrategyService
from app.services.ai.deterministic_provider import DeterministicAIProvider

class BacktestEngine:
    """
    High-performance historical simulation engine.
    Replays historical price candles bar-by-bar, generates objective market context snapshots,
    and evaluates versioned natural-language session instructions.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.provider = DeterministicAIProvider()

    async def run_backtest(self, req: BacktestRequest, user_id: int = 1) -> BacktestResultRead:
        symbol = req.symbol.upper()
        timeframe = req.timeframe
        session_name = req.session_name.lower()

        # 1. Fetch Instrument
        inst_res = await self.db.execute(select(Instrument).where(Instrument.symbol == symbol))
        instrument = inst_res.scalar_one_or_none()
        if not instrument:
            raise ValueError(f"Instrument '{symbol}' not found.")

        # 2. Fetch all candles in range + 30 bars buffer before start_date
        stmt = (
            select(Candle)
            .where(
                Candle.instrument_id == instrument.id,
                Candle.timeframe == timeframe,
                Candle.timestamp_utc <= req.end_date,
            )
            .order_by(Candle.timestamp_utc.asc())
        )
        c_res = await self.db.execute(stmt)
        all_candles = [CandleRead.model_validate(c) for c in c_res.scalars().all()]

        if len(all_candles) < 5:
            raise ValueError(f"Insufficient historical candles ({len(all_candles)}) to run backtest.")

        # Fetch daily candles
        d_stmt = (
            select(Candle)
            .where(Candle.instrument_id == instrument.id, Candle.timeframe == "1d")
            .order_by(Candle.timestamp_utc.asc())
        )
        d_res = await self.db.execute(d_stmt)
        daily_candles = [CandleRead.model_validate(c) for c in d_res.scalars().all()]

        # 3. Resolve Instructions
        strat_svc = StrategyService(self.db)
        instruction_text = req.custom_instructions
        instruction_version_id = req.instruction_version_id

        if not instruction_text:
            if instruction_version_id:
                iv = await strat_svc.get_active_version(instruction_version_id, 1) # or query by id
                # query by id directly
                from app.models.strategy import InstructionVersion
                stmt_v = select(InstructionVersion).where(InstructionVersion.id == instruction_version_id)
                res_v = await self.db.execute(stmt_v)
                v_obj = res_v.scalar_one_or_none()
                if v_obj:
                    instruction_text = v_obj.prompt_content
            else:
                inst = await strat_svc.get_or_create_instruction(user_id, session_name)
                act_v = await strat_svc.get_active_version(inst.id, inst.current_version)
                if act_v:
                    instruction_version_id = act_v.id
                    instruction_text = act_v.prompt_content

        if not instruction_text:
            instruction_text = "Default session evaluation instructions."

        pip_size = float(instrument.pip_size) if instrument.pip_size else 0.0001
        state_counts: Dict[str, int] = defaultdict(int)
        setups: List[Dict[str, Any]] = []

        def _as_utc(d: datetime) -> datetime:
            return d.astimezone(timezone.utc) if d.tzinfo else d.replace(tzinfo=timezone.utc)

        start_dt = _as_utc(req.start_date)
        end_dt = _as_utc(req.end_date)

        # Find starting index (first candle >= start_date with at least 5 prior bars)
        start_idx = 5
        for i, c in enumerate(all_candles):
            if _as_utc(c.timestamp_utc) >= start_dt and i >= 5:
                start_idx = i
                break

        analyzed_count = 0
        # 4. Step through candles
        for idx in range(start_idx, len(all_candles)):
            curr_bar = all_candles[idx]
            curr_utc = _as_utc(curr_bar.timestamp_utc)
            if curr_utc > end_dt:
                break

            # Filter candles up to current bar (max 60 window for indicators)
            window = all_candles[max(0, idx - 59): idx + 1]

            # Generate context
            context = MarketContextEngine.generate_context(
                symbol=symbol,
                timeframe=timeframe,
                candles=window,
                daily_candles=[d for d in daily_candles if _as_utc(d.timestamp_utc) <= curr_utc],
                pip_size=pip_size,
            )

            # Evaluate with AI Provider
            eval_result = await self.provider.analyze(
                market_context=context.model_dump(),
                user_instructions=instruction_text,
            )

            state_val = eval_result.state.value
            state_counts[state_val] += 1
            analyzed_count += 1

            if eval_result.state in [
                AnalysisStateEnum.WATCH,
                AnalysisStateEnum.POTENTIAL_SETUP,
                AnalysisStateEnum.VALID_SETUP,
            ]:
                setups.append({
                    "timestamp_utc": curr_bar.timestamp_utc.isoformat(),
                    "price": curr_bar.close,
                    "state": state_val,
                    "summary": eval_result.summary,
                    "condition_breakdown": [c.model_dump() for c in eval_result.condition_breakdown],
                })

        # 5. Persist Backtest Record
        bt_record = Backtest(
            user_id=user_id,
            instruction_version_id=instruction_version_id,
            instrument_id=instrument.id,
            timeframe=timeframe,
            session_name=session_name,
            start_date=req.start_date,
            end_date=req.end_date,
            total_candles_analyzed=analyzed_count,
            state_distribution=dict(state_counts),
            identified_setups=setups,
            status="COMPLETED",
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(bt_record)
        await self.db.commit()
        await self.db.refresh(bt_record)

        return BacktestResultRead(
            id=bt_record.id,
            symbol=symbol,
            instrument_id=instrument.id,
            timeframe=timeframe,
            session_name=session_name,
            instruction_version_id=instruction_version_id,
            start_date=req.start_date,
            end_date=req.end_date,
            total_candles_analyzed=analyzed_count,
            state_distribution=dict(state_counts),
            identified_setups=setups,
            status=bt_record.status,
            created_at=bt_record.created_at,
        )

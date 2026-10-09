from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.candle import CandleRead
from app.models.trade_outcome import TradeSetupOutcome

class TradeOutcomeTracker:
    """
    Simulates, measures, and records the post-signal lifecycle of a TradeSetup:
    - Fill status and slippage (signal price vs actual fill price)
    - Max Favorable Excursion (MFE) in price units and R-multiples
    - Max Adverse Excursion (MAE) in price units and R-multiples
    - Milestone tracking (Did the setup reach 1R? 2R? 3R? 5R? 10R? 20R?)
    - Time-to-hit metrics (seconds to entry, 1R, TP, SL)
    - Final outcome determination (TP_HIT, SL_HIT, ACTIVE, EXPIRED)
    """

    @classmethod
    def evaluate_candles_lifecycle(
        cls,
        setup_id: str,
        symbol: str,
        action: str,
        entry: float,
        stop_loss: float,
        take_profit: float,
        signal_timestamp_utc: datetime,
        subsequent_candles: List[CandleRead],
        fill_price: Optional[float] = None,
        tp1: Optional[float] = None,
        tp2: Optional[float] = None,
        setup_snapshot: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        is_long = "BUY" in action.upper() or "LONG" in action.upper()
        # For calculation reference, use actual fill if known, else signal entry
        eff_entry = float(fill_price) if fill_price is not None else float(entry)
        slippage = round(fill_price - entry, 5) if fill_price is not None else None

        risk_dist = round(abs(eff_entry - stop_loss), 5)
        safe_risk = max(risk_dist, 1e-6)

        tp_target = tp2 or take_profit

        # Sort chronological
        candles = sorted(
            subsequent_candles,
            key=lambda c: c.timestamp_utc if c.timestamp_utc.tzinfo else c.timestamp_utc.replace(tzinfo=timezone.utc)
        )

        # Track limit reach vs confirmed fill
        limit_reached = fill_price is not None
        entry_time = signal_timestamp_utc if fill_price is not None else None
        exit_time = None
        outcome = "ACTIVE" if fill_price is not None else "PENDING"

        max_fav = 0.0
        max_adv = 0.0

        time_to_entry = None
        time_to_1r = None
        time_to_2r = None
        time_to_3r = None
        time_to_5r = None
        time_to_10r = None
        time_to_20r = None
        time_to_tp = None
        time_to_sl = None

        reached_1r = False
        reached_2r = False
        reached_3r = False
        reached_5r = False
        reached_10r = False
        reached_20r = False

        realized_r = None

        if signal_timestamp_utc.tzinfo is None:
            sig_ts = signal_timestamp_utc.replace(tzinfo=timezone.utc)
        else:
            sig_ts = signal_timestamp_utc.astimezone(timezone.utc)

        for c in candles:
            c_ts = c.timestamp_utc if c.timestamp_utc.tzinfo else c.timestamp_utc.replace(tzinfo=timezone.utc)

            # Check if limit entry was reached by subsequent price action
            if not limit_reached:
                if is_long:
                    # BUY LIMIT triggers if price dips to or below entry
                    if float(c.low) <= entry:
                        limit_reached = True
                        entry_time = c_ts
                        time_to_entry = (c_ts - sig_ts).total_seconds()
                        outcome = "ACTIVE"
                else:
                    # SELL LIMIT triggers if price rises to or above entry
                    if float(c.high) >= entry:
                        limit_reached = True
                        entry_time = c_ts
                        time_to_entry = (c_ts - sig_ts).total_seconds()
                        outcome = "ACTIVE"

            if not limit_reached:
                continue

            # Tracking while ACTIVE
            if is_long:
                fav = max(0.0, float(c.high) - eff_entry)
                adv = max(0.0, eff_entry - float(c.low))
                if fav > max_fav:
                    max_fav = fav
                if adv > max_adv:
                    max_adv = adv

                r_fav = max_fav / safe_risk

                # Milestone checks
                if r_fav >= 1.0 and not reached_1r:
                    reached_1r = True
                    time_to_1r = (c_ts - sig_ts).total_seconds()
                if r_fav >= 2.0 and not reached_2r:
                    reached_2r = True
                    time_to_2r = (c_ts - sig_ts).total_seconds()
                if r_fav >= 3.0 and not reached_3r:
                    reached_3r = True
                    time_to_3r = (c_ts - sig_ts).total_seconds()
                if r_fav >= 5.0 and not reached_5r:
                    reached_5r = True
                    time_to_5r = (c_ts - sig_ts).total_seconds()
                if r_fav >= 10.0 and not reached_10r:
                    reached_10r = True
                    time_to_10r = (c_ts - sig_ts).total_seconds()
                if r_fav >= 20.0 and not reached_20r:
                    reached_20r = True
                    time_to_20r = (c_ts - sig_ts).total_seconds()

                sl_hit = float(c.low) <= stop_loss
                tp_hit = float(c.high) >= tp_target

                # Ambiguous intrabar breach: both TP and SL hit in same candle
                if sl_hit and tp_hit:
                    outcome = "AMBIGUOUS_INTRABAR"
                    exit_time = c_ts
                    time_to_sl = (c_ts - sig_ts).total_seconds()
                    time_to_tp = time_to_sl
                    realized_r = 0.0
                    break
                elif sl_hit:
                    outcome = "SL_HIT"
                    exit_time = c_ts
                    time_to_sl = (c_ts - sig_ts).total_seconds()
                    realized_r = -1.0
                    break
                elif tp_hit:
                    outcome = "TP_HIT"
                    exit_time = c_ts
                    time_to_tp = (c_ts - sig_ts).total_seconds()
                    realized_r = round((tp_target - eff_entry) / safe_risk, 2)
                    break

            else:  # is_short
                fav = max(0.0, eff_entry - float(c.low))
                adv = max(0.0, float(c.high) - eff_entry)
                if fav > max_fav:
                    max_fav = fav
                if adv > max_adv:
                    max_adv = adv

                r_fav = max_fav / safe_risk

                if r_fav >= 1.0 and not reached_1r:
                    reached_1r = True
                    time_to_1r = (c_ts - sig_ts).total_seconds()
                if r_fav >= 2.0 and not reached_2r:
                    reached_2r = True
                    time_to_2r = (c_ts - sig_ts).total_seconds()
                if r_fav >= 3.0 and not reached_3r:
                    reached_3r = True
                    time_to_3r = (c_ts - sig_ts).total_seconds()
                if r_fav >= 5.0 and not reached_5r:
                    reached_5r = True
                    time_to_5r = (c_ts - sig_ts).total_seconds()
                if r_fav >= 10.0 and not reached_10r:
                    reached_10r = True
                    time_to_10r = (c_ts - sig_ts).total_seconds()
                if r_fav >= 20.0 and not reached_20r:
                    reached_20r = True
                    time_to_20r = (c_ts - sig_ts).total_seconds()

                sl_hit = float(c.high) >= stop_loss
                tp_hit = float(c.low) <= tp_target

                # Ambiguous intrabar breach: both TP and SL hit in same candle
                if sl_hit and tp_hit:
                    outcome = "AMBIGUOUS_INTRABAR"
                    exit_time = c_ts
                    time_to_sl = (c_ts - sig_ts).total_seconds()
                    time_to_tp = time_to_sl
                    realized_r = 0.0
                    break
                elif sl_hit:
                    outcome = "SL_HIT"
                    exit_time = c_ts
                    time_to_sl = (c_ts - sig_ts).total_seconds()
                    realized_r = -1.0
                    break
                elif tp_hit:
                    outcome = "TP_HIT"
                    exit_time = c_ts
                    time_to_tp = (c_ts - sig_ts).total_seconds()
                    realized_r = round((eff_entry - tp_target) / safe_risk, 2)
                    break

        mfe_r = round(max_fav / safe_risk, 4) if risk_dist > 0 else 0.0
        mae_r = round(max_adv / safe_risk, 4) if risk_dist > 0 else 0.0

        return {
            "setup_id": setup_id,
            "symbol": symbol,
            "direction": "BUY" if is_long else "SELL",
            "entry_signal": entry,
            "fill_price": fill_price,  # Only known if confirmed broker fill provided
            "slippage": slippage,
            "stop_loss": stop_loss,
            "take_profit": tp_target,
            "signal_timestamp_utc": sig_ts,
            "entry_timestamp_utc": entry_time,
            "exit_timestamp_utc": exit_time,
            "max_favorable_excursion": round(max_fav, 5),
            "max_adverse_excursion": round(max_adv, 5),
            "mfe_r_multiple": mfe_r,
            "mae_r_multiple": mae_r,
            "time_to_entry_seconds": time_to_entry,
            "time_to_1r_seconds": time_to_1r,
            "time_to_2r_seconds": time_to_2r,
            "time_to_3r_seconds": time_to_3r,
            "time_to_5r_seconds": time_to_5r,
            "time_to_tp_seconds": time_to_tp,
            "time_to_sl_seconds": time_to_sl,
            "reached_1r": reached_1r,
            "reached_2r": reached_2r,
            "reached_3r": reached_3r,
            "reached_5r": reached_5r,
            "reached_10r": reached_10r,
            "reached_20r": reached_20r,
            "outcome": outcome,
            "realized_r_multiple": realized_r,
            "setup_snapshot": setup_snapshot or {},
        }

    @classmethod
    async def persist_candidate_setup(
        cls,
        db_session: AsyncSession,
        setup_id: str,
        symbol: str,
        direction: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        signal_timestamp_utc: datetime,
        setup_snapshot: Optional[Dict[str, Any]] = None,
    ) -> TradeSetupOutcome:
        """
        Persists a candidate setup uniquely identified and idempotently.
        Preserves original setup context with UTC timestamps.
        """
        if signal_timestamp_utc.tzinfo is None:
            sig_ts = signal_timestamp_utc.replace(tzinfo=timezone.utc)
        else:
            sig_ts = signal_timestamp_utc.astimezone(timezone.utc)

        data = {
            "setup_id": setup_id,
            "symbol": symbol.upper(),
            "direction": direction.upper(),
            "entry_signal": entry_price,
            "fill_price": None,  # Not known yet; not simulating broker fill
            "slippage": None,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "signal_timestamp_utc": sig_ts,
            "outcome": "PENDING",
            "setup_snapshot": setup_snapshot or {},
        }
        return await cls.persist_outcome(db_session, data)

    @classmethod
    async def update_active_outcomes(
        cls,
        db_session: AsyncSession,
        symbol: Optional[str] = None,
    ) -> List[TradeSetupOutcome]:
        """
        Monitors subsequent market candles for all PENDING and ACTIVE setups.
        Records limit reach, MFE, MAE, R milestones, and final TP/SL/Ambiguous outcomes.
        Idempotent: repeatedly executing across the same candle history maintains state consistency.
        """
        from app.models.candle import Candle
        from app.models.instrument import Instrument

        query = select(TradeSetupOutcome).where(TradeSetupOutcome.outcome.in_(["PENDING", "ACTIVE"]))
        if symbol:
            query = query.where(TradeSetupOutcome.symbol == symbol.upper())

        res = await db_session.execute(query)
        active_setups = list(res.scalars().all())

        updated_records = []
        for setup in active_setups:
            # Fetch subsequent candles chronologically
            c_stmt = (
                select(Candle)
                .join(Instrument, Candle.instrument_id == Instrument.id)
                .where(
                    Instrument.symbol == setup.symbol.upper(),
                    Candle.timestamp_utc > setup.signal_timestamp_utc,
                )
                .order_by(Candle.timestamp_utc.asc())
                .limit(200)
            )
            c_res = await db_session.execute(c_stmt)
            candles_raw = c_res.scalars().all()
            if not candles_raw:
                continue

            subsequent_candles = [CandleRead.model_validate(c) for c in candles_raw]

            evaluated = cls.evaluate_candles_lifecycle(
                setup_id=setup.setup_id,
                symbol=setup.symbol,
                action=setup.direction,
                entry=float(setup.entry_signal),
                stop_loss=float(setup.stop_loss),
                take_profit=float(setup.take_profit),
                signal_timestamp_utc=setup.signal_timestamp_utc,
                subsequent_candles=subsequent_candles,
                fill_price=float(setup.fill_price) if setup.fill_price is not None else None,
                setup_snapshot=setup.setup_snapshot,
            )

            # Idempotently update setup attributes
            for k, v in evaluated.items():
                if hasattr(setup, k):
                    setattr(setup, k, v)
            updated_records.append(setup)

        if updated_records:
            await db_session.commit()
            for r in updated_records:
                await db_session.refresh(r)

        return updated_records

    @classmethod
    async def persist_outcome(
        cls,
        db_session: AsyncSession,
        outcome_data: Dict[str, Any],
    ) -> TradeSetupOutcome:
        """Persists or updates TradeSetupOutcome idempotently."""
        setup_id = outcome_data["setup_id"]
        stmt = select(TradeSetupOutcome).where(TradeSetupOutcome.setup_id == setup_id)
        res = await db_session.execute(stmt)
        existing = res.scalar_one_or_none()

        if existing:
            for k, v in outcome_data.items():
                if hasattr(existing, k):
                    setattr(existing, k, v)
            await db_session.commit()
            await db_session.refresh(existing)
            return existing

        new_row = TradeSetupOutcome(**outcome_data)
        db_session.add(new_row)
        await db_session.commit()
        await db_session.refresh(new_row)
        return new_row

    @classmethod
    def initialize_outcome(
        cls,
        setup_id: str,
        symbol: str,
        direction: str,
        signal_entry: float,
        stop_loss: float,
        take_profit: float,
        signal_timestamp: datetime,
        tp1: Optional[float] = None,
        tp2: Optional[float] = None,
        setup_snapshot: Optional[Dict[str, Any]] = None,
    ) -> TradeSetupOutcome:
        """Initializes a new in-memory TradeSetupOutcome for tracking."""
        return TradeSetupOutcome(
            setup_id=setup_id,
            symbol=symbol,
            direction=direction.upper(),
            entry_signal=signal_entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            signal_timestamp_utc=signal_timestamp,
            slippage=0.0,
            outcome="PENDING",
            max_favorable_excursion=0.0,
            max_adverse_excursion=0.0,
            mfe_r_multiple=0.0,
            mae_r_multiple=0.0,
            reached_1r=False,
            reached_2r=False,
            reached_3r=False,
            reached_5r=False,
            reached_10r=False,
            reached_20r=False,
            reached_sl=False,
            reached_tp=False,
            setup_snapshot=setup_snapshot or {},
        )

    @classmethod
    def record_fill(
        cls,
        outcome: TradeSetupOutcome,
        fill_price: float,
        fill_timestamp: datetime,
    ) -> TradeSetupOutcome:
        """Records the actual broker/order fill price and execution timestamp."""
        outcome.fill_price = fill_price
        outcome.entry_timestamp_utc = fill_timestamp
        entry = float(outcome.entry_signal)
        if outcome.direction == "BUY":
            outcome.slippage = round(fill_price - entry, 5)
        else:
            outcome.slippage = round(entry - fill_price, 5)
        outcome.outcome = "FILLED"
        outcome.time_to_entry_seconds = (fill_timestamp - outcome.signal_timestamp_utc).total_seconds()
        return outcome

    @classmethod
    def update_price_tick(
        cls,
        outcome: TradeSetupOutcome,
        high: float,
        low: float,
        timestamp: datetime,
    ) -> TradeSetupOutcome:
        """Updates MFE, MAE, R milestones, and SL/TP hits for an active trade."""
        eff_entry = float(outcome.fill_price) if outcome.fill_price is not None else float(outcome.entry_signal)
        sl = float(outcome.stop_loss)
        tp = float(outcome.take_profit)
        sig_ts = outcome.signal_timestamp_utc

        risk = max(abs(eff_entry - sl), 1e-6)
        is_long = outcome.direction == "BUY"

        if is_long:
            fav = max(float(outcome.max_favorable_excursion), high - eff_entry)
            adv = max(float(outcome.max_adverse_excursion), eff_entry - low)
            outcome.max_favorable_excursion = round(fav, 5)
            outcome.max_adverse_excursion = round(adv, 5)
            r_fav = fav / risk

            if r_fav >= 1.0 and not outcome.reached_1r:
                outcome.reached_1r = True
                outcome.time_to_1r_seconds = (timestamp - sig_ts).total_seconds()
            if r_fav >= 2.0 and not outcome.reached_2r:
                outcome.reached_2r = True
                outcome.time_to_2r_seconds = (timestamp - sig_ts).total_seconds()
            if r_fav >= 3.0 and not outcome.reached_3r:
                outcome.reached_3r = True
                outcome.time_to_3r_seconds = (timestamp - sig_ts).total_seconds()
            if r_fav >= 5.0 and not outcome.reached_5r:
                outcome.reached_5r = True
                outcome.time_to_5r_seconds = (timestamp - sig_ts).total_seconds()
            if r_fav >= 10.0 and not outcome.reached_10r:
                outcome.reached_10r = True
                outcome.time_to_10r_seconds = (timestamp - sig_ts).total_seconds()
            if r_fav >= 20.0 and not outcome.reached_20r:
                outcome.reached_20r = True
                outcome.time_to_20r_seconds = (timestamp - sig_ts).total_seconds()

            if low <= sl:
                outcome.reached_sl = True
                outcome.outcome = "STOPPED_OUT"
                outcome.exit_timestamp_utc = timestamp
                outcome.time_to_sl_seconds = (timestamp - sig_ts).total_seconds()
                outcome.final_r_multiple = -1.0
            elif high >= tp:
                outcome.reached_tp = True
                outcome.outcome = "TP_HIT"
                outcome.exit_timestamp_utc = timestamp
                outcome.time_to_tp_seconds = (timestamp - sig_ts).total_seconds()
                outcome.final_r_multiple = round((tp - eff_entry) / risk, 2)
        else:
            fav = max(float(outcome.max_favorable_excursion), eff_entry - low)
            adv = max(float(outcome.max_adverse_excursion), high - eff_entry)
            outcome.max_favorable_excursion = round(fav, 5)
            outcome.max_adverse_excursion = round(adv, 5)
            r_fav = fav / risk

            if r_fav >= 1.0 and not outcome.reached_1r:
                outcome.reached_1r = True
                outcome.time_to_1r_seconds = (timestamp - sig_ts).total_seconds()
            if r_fav >= 2.0 and not outcome.reached_2r:
                outcome.reached_2r = True
                outcome.time_to_2r_seconds = (timestamp - sig_ts).total_seconds()
            if r_fav >= 3.0 and not outcome.reached_3r:
                outcome.reached_3r = True
                outcome.time_to_3r_seconds = (timestamp - sig_ts).total_seconds()
            if r_fav >= 5.0 and not outcome.reached_5r:
                outcome.reached_5r = True
                outcome.time_to_5r_seconds = (timestamp - sig_ts).total_seconds()
            if r_fav >= 10.0 and not outcome.reached_10r:
                outcome.reached_10r = True
                outcome.time_to_10r_seconds = (timestamp - sig_ts).total_seconds()
            if r_fav >= 20.0 and not outcome.reached_20r:
                outcome.reached_20r = True
                outcome.time_to_20r_seconds = (timestamp - sig_ts).total_seconds()

            if high >= sl:
                outcome.reached_sl = True
                outcome.outcome = "STOPPED_OUT"
                outcome.exit_timestamp_utc = timestamp
                outcome.time_to_sl_seconds = (timestamp - sig_ts).total_seconds()
                outcome.final_r_multiple = -1.0
            elif low <= tp:
                outcome.reached_tp = True
                outcome.outcome = "TP_HIT"
                outcome.exit_timestamp_utc = timestamp
                outcome.time_to_tp_seconds = (timestamp - sig_ts).total_seconds()
                outcome.final_r_multiple = round((eff_entry - tp) / risk, 2)

        return outcome

    @classmethod
    def get_historical_statistics(
        cls,
        symbol: str,
        setups_history: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        """
        Calculates empirical historical outcome statistics.
        CRITICAL CONSTRAINT: Never manufactures probabilities (e.g. '20R has 80% probability').
        If sample_size is 0 or insufficient, explicitly flags INSUFFICIENT_DATA.
        """
        if not setups_history or len(setups_history) == 0:
            return {
                "symbol": symbol,
                "sample_size": 0,
                "statistics_status": "INSUFFICIENT_DATA",
                "win_rate": None,
                "avg_r_multiple": None,
                "reaches_1r": None,
                "reaches_2r": None,
                "reaches_5r": None,
                "reaches_20r": None,
            }

        total = len(setups_history)
        wins = sum(1 for s in setups_history if getattr(s, "outcome", None) in ["TP_HIT", "TP1_HIT", "TP2_HIT"])
        r_mults = [float(getattr(s, "realized_r_multiple", 0.0) or 0.0) for s in setups_history if getattr(s, "realized_r_multiple", None) is not None]

        r1_hits = sum(1 for s in setups_history if getattr(s, "reached_1r", False))
        r2_hits = sum(1 for s in setups_history if getattr(s, "reached_2r", False))
        r5_hits = sum(1 for s in setups_history if getattr(s, "reached_5r", False))
        r20_hits = sum(1 for s in setups_history if getattr(s, "reached_20r", False))

        return {
            "symbol": symbol,
            "sample_size": total,
            "statistics_status": "VALID" if total >= 30 else "LOW_SAMPLE_WARNING",
            "win_rate": round(wins / total, 4),
            "avg_r_multiple": round(sum(r_mults) / len(r_mults), 2) if r_mults else 0.0,
            "reaches_1r": round(r1_hits / total, 4),
            "reaches_2r": round(r2_hits / total, 4),
            "reaches_5r": round(r5_hits / total, 4),
            "reaches_20r": round(r20_hits / total, 4),
        }

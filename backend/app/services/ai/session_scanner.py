import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy import select

from app.core.database import async_session_factory
from app.models.instrument import Instrument
from app.models.analysis import AnalysisStateEnum
from app.schemas.ai_analysis import AIAnalysisRequest
from app.schemas.notification import NotificationRuleConfig
from app.services.session import SessionEngine
from app.services.ai import AIAnalysisEngine
from app.services.notifications import NotificationService
from app.services.tracking.outcome_tracker import TradeOutcomeTracker

logger = logging.getLogger("forex_ai.session_scanner")

class SessionScannerWorker:
    """
    Automated Continuous Background Session Scanner.
    Autonomously scans watchlist instruments 24/7 across Asian, London, and New York sessions.
    Evaluates primary Malaysian Support and Resistance (MSNR) & Alchemist rules (zero repainting, closed candle wicks,
    RBS/SBR flip zones, 50% Consequent Encroachment CE, MISS liquidity sweeps, and Daily Profile #2 NY Reversal SMT)
    and dispatches high-priority push notifications to trader mobile devices before order execution.
    """

    def __init__(self, scan_interval_seconds: int = 45):
        self.scan_interval_seconds = scan_interval_seconds
        self._is_running = False
        self._task: Optional[asyncio.Task] = None
        self._total_scans = 0
        self._last_scan_utc: Optional[datetime] = None
        self._last_active_session: Optional[str] = None
        self._last_results: List[Dict[str, Any]] = []
        self._total_notifications_sent = 0
        self._last_error: Optional[str] = None
        self._last_state_counts: Dict[str, int] = {
            "NO_SETUP": 0,
            "WATCH": 0,
            "POTENTIAL": 0,
            "VALID": 0,
        }

    async def start(self) -> None:
        """Starts the autonomous scanner background task."""
        if self._is_running:
            logger.warning("SessionScannerWorker is already running.")
            return

        self._is_running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"SessionScannerWorker started with {self.scan_interval_seconds}s cycle interval.")

    async def stop(self) -> None:
        """Gracefully stops the scanner background task."""
        self._is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("SessionScannerWorker stopped successfully.")

    async def _run_loop(self) -> None:
        # Initial brief wait to let DB initialization and ingestion worker settle
        await asyncio.sleep(5)
        while self._is_running:
            try:
                await self.scan_cycle()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._last_error = str(e)
                logger.error(f"Error during SessionScanner cycle: {e}", exc_info=True)

            try:
                await asyncio.sleep(self.scan_interval_seconds)
            except asyncio.CancelledError:
                break

    async def scan_cycle(self) -> Dict[str, Any]:
        """
        Executes a single scan cycle across all active watchlist instruments.
        Can be called by the background loop or triggered manually via API.
        """
        now_utc = datetime.now(timezone.utc)
        self._last_scan_utc = now_utc
        self._total_scans += 1

        # 1. Determine Current Active Session
        curr_session_state = SessionEngine.evaluate_sessions(now_utc)
        active_session = curr_session_state.primary_session or (
            curr_session_state.active_sessions[0] if curr_session_state.active_sessions else "london"
        )
        self._last_active_session = active_session

        cycle_results: List[Dict[str, Any]] = []
        setups_found = 0

        async with async_session_factory() as db:
            try:
                # 2. Query Active Watchlist Instruments
                stmt = select(Instrument).where(Instrument.is_active == True)
                res = await db.execute(stmt)
                instruments = res.scalars().all()

                if not instruments:
                    logger.debug("No active instruments found in database for scanner cycle.")
                    return {
                        "timestamp_utc": now_utc.isoformat(),
                        "session": active_session,
                        "scanned_count": 0,
                        "setups_found": 0,
                        "results": [],
                    }

                notif_config = NotificationService.DEFAULT_CONFIG
                notif_svc = NotificationService(db)
                ai_engine = AIAnalysisEngine(db)

                # Institutional execution timeframes to scan
                timeframes = ["5m", "15m"]

                # 3. Scan UT Bot for User-Selected Pairs Only
                if notif_config.notify_on_ut_bot and notif_config.ut_bot_pairs:
                    from app.services.ai.ut_bot import UTBotEngine
                    from app.models.candle import Candle
                    from app.schemas.candle import CandleRead
                    from sqlalchemy import desc

                    for ut_sym in notif_config.ut_bot_pairs:
                        ut_sym_upper = ut_sym.upper()
                        inst_match = next((i for i in instruments if i.symbol.upper() == ut_sym_upper), None)
                        if not inst_match:
                            continue

                        for tf in timeframes:
                            try:
                                c_stmt = (
                                    select(Candle)
                                    .where(Candle.instrument_id == inst_match.id, Candle.timeframe == tf)
                                    .order_by(desc(Candle.timestamp_utc))
                                    .limit(60)
                                )
                                c_res = await db.execute(c_stmt)
                                candles = [CandleRead.model_validate(c) for c in reversed(c_res.scalars().all())]
                                if len(candles) >= 10:
                                    sens = 1.5 if ("R_" in ut_sym_upper or "VOLATILITY" in ut_sym_upper or "1HZ" in ut_sym_upper) else 1.2
                                    ut_eval = UTBotEngine.evaluate(
                                        candles,
                                        sensitivity=sens,
                                        atr_period=10,
                                        symbol=ut_sym_upper,
                                        timeframe=tf,
                                    )
                                    if ut_eval.get("signal") in ["BUY", "SELL"]:
                                        logger.info(f"⚡ [SessionScanner] UT Bot {ut_eval['signal']} on selected pair {ut_sym_upper} ({tf})")
                                        notif_record = await notif_svc.dispatch_ut_bot_alert(
                                            symbol=ut_sym_upper,
                                            timeframe=tf,
                                            ut_result=ut_eval,
                                            user_id=1,
                                            rule_cfg=notif_config,
                                        )
                                        if notif_record:
                                            self._total_notifications_sent += 1
                                            logger.info(f"📱 [SessionScanner] Dispatched UT Bot push alert #{notif_record.id} for {ut_sym_upper}")
                            except Exception as ut_err:
                                logger.debug(f"[SessionScanner] UT Bot error on {ut_sym_upper} ({tf}): {ut_err}")

                for inst in instruments:
                    symbol = inst.symbol.upper()
                    is_24_7 = any(k in symbol for k in ["R_", "VOLATILITY", "1HZ", "BOOM", "CRASH", "BTC", "ETH"])
                    effective_session = "CONTINUOUS_24_7" if is_24_7 else active_session
                    for tf in timeframes:
                        try:
                            req = AIAnalysisRequest(
                                symbol=symbol,
                                timeframe=tf,
                                session_name=effective_session,
                            )
                            analysis_record = await ai_engine.execute_analysis(req)

                            # Extract 7H status + direction
                            p_7h = None
                            if analysis_record.structured_state and analysis_record.structured_state.seven_hour_profile:
                                p_7h = analysis_record.structured_state.seven_hour_profile
                            elif analysis_record.market_context and analysis_record.market_context.get("seven_hour_profile"):
                                p_7h = analysis_record.market_context["seven_hour_profile"]

                            if p_7h:
                                if isinstance(p_7h, dict):
                                    h7_stat = str(p_7h.get("status", "UNKNOWN")).upper()
                                    h7_dir = str(p_7h.get("direction", "UNKNOWN")).upper()
                                else:
                                    h7_stat = str(getattr(p_7h.status, "value", p_7h.status)).upper()
                                    h7_dir = str(getattr(p_7h.direction, "value", p_7h.direction)).upper()
                            else:
                                h7_stat, h7_dir = "NONE", "NONE"
                            h7_str = f"{h7_stat}+{h7_dir}"

                            # Determine which session levels exist
                            levels_exist = []
                            if analysis_record.structured_state and analysis_record.structured_state.session and analysis_record.structured_state.session.session_levels:
                                for s_name, s_lvl in analysis_record.structured_state.session.session_levels.items():
                                    if getattr(s_lvl, "high", None) is not None:
                                        levels_exist.append(s_name)
                            elif analysis_record.market_context and analysis_record.market_context.get("session_state"):
                                s_lvls = analysis_record.market_context["session_state"].get("session_levels", {})
                                for s_name, s_lvl in s_lvls.items():
                                    if isinstance(s_lvl, dict) and s_lvl.get("high") is not None:
                                        levels_exist.append(s_name)
                            levels_str = ",".join(levels_exist) if levels_exist else "none"

                            # Determine the first failed condition
                            first_failed = "none"
                            for c in analysis_record.condition_breakdown:
                                if not c.satisfied:
                                    first_failed = c.condition
                                    break

                            # Log one line per symbol/timeframe
                            logger.info(
                                f"🔍 [{symbol} {tf}] session={effective_session}, "
                                f"7H={h7_str}, "
                                f"levels=[{levels_str}], "
                                f"first_failed={first_failed}"
                            )

                            item_res = {
                                "symbol": symbol,
                                "timeframe": tf,
                                "session": effective_session,
                                "state": analysis_record.state.value,
                                "summary": analysis_record.summary,
                                "timestamp": analysis_record.timestamp_utc.isoformat(),
                            }
                            cycle_results.append(item_res)

                            # If setup confirmed, dispatch push notification (suppressing unconfirmed noise)
                            if analysis_record.state == AnalysisStateEnum.VALID_SETUP or (
                                notif_config.notify_on_potential_setup and analysis_record.state == AnalysisStateEnum.POTENTIAL_SETUP
                            ):
                                setups_found += 1
                                logger.info(
                                    f"🎯 [SessionScanner] {analysis_record.state.value} on {symbol} ({tf}) in {active_session}: {analysis_record.summary}"
                                )
                                notif_record = await notif_svc.evaluate_and_dispatch(
                                    analysis=analysis_record,
                                    user_id=1,
                                    config=notif_config,
                                )
                                if notif_record:
                                    self._total_notifications_sent += 1
                                    logger.info(
                                        f"📱 [SessionScanner] Dispatched push notification #{notif_record.id} for {symbol}"
                                    )

                        except ValueError as ve:
                            # Not enough candles yet for this symbol/tf, silently ignore
                            logger.debug(f"[SessionScanner] Skipping {symbol} {tf}: {ve}")
                        except Exception as e:
                            logger.warning(f"[SessionScanner] Error analyzing {symbol} {tf}: {e}")

                # 4. Monitor post-signal candle lifecycle for all active/pending setups
                try:
                    tracked_outcomes = await TradeOutcomeTracker.update_active_outcomes(db)
                    if tracked_outcomes:
                        logger.info(f"📊 [SessionScanner] Updated {len(tracked_outcomes)} active/pending trade outcomes.")
                except Exception as track_err:
                    logger.debug(f"[SessionScanner] Outcome tracker cycle error: {track_err}")

            except Exception as exc:
                self._last_error = str(exc)
                logger.error(f"[SessionScanner] Database session error: {exc}", exc_info=True)

        state_counts = {
            "NO_SETUP": 0,
            "WATCH": 0,
            "POTENTIAL": 0,
            "VALID": 0,
        }
        for r in cycle_results:
            st = r.get("state")
            if st == AnalysisStateEnum.VALID_SETUP.value:
                state_counts["VALID"] += 1
            elif st == AnalysisStateEnum.POTENTIAL_SETUP.value:
                state_counts["POTENTIAL"] += 1
            elif st == AnalysisStateEnum.WATCH.value:
                state_counts["WATCH"] += 1
            else:
                state_counts["NO_SETUP"] += 1

        self._last_state_counts = state_counts
        self._last_results = cycle_results[-30:]
        logger.info(
            f"🔄 [SessionScanner] Cycle #{self._total_scans} completed for [{active_session.upper()}]. "
            f"Evaluated {len(cycle_results)} symbol/TF pairs, found {setups_found} active setup(s). "
            f"State Counts: NO_SETUP={state_counts['NO_SETUP']}, WATCH={state_counts['WATCH']}, "
            f"POTENTIAL={state_counts['POTENTIAL']}, VALID={state_counts['VALID']}"
        )

        return {
            "timestamp_utc": now_utc.isoformat(),
            "session": active_session,
            "scanned_count": len(cycle_results),
            "setups_found": setups_found,
            "state_counts": state_counts,
            "results": cycle_results,
        }

    def get_status(self) -> Dict[str, Any]:
        """Returns the real-time health and execution statistics of the scanner."""
        return {
            "is_running": self._is_running,
            "scan_interval_seconds": self.scan_interval_seconds,
            "total_scans_completed": self._total_scans,
            "total_notifications_sent": self._total_notifications_sent,
            "last_scan_utc": self._last_scan_utc.isoformat() if self._last_scan_utc else None,
            "last_active_session": self._last_active_session,
            "state_counts": self._last_state_counts,
            "recent_results": self._last_results[-10:],
            "last_error": self._last_error,
        }

# Global singleton scanner worker instance
_scanner_instance: Optional[SessionScannerWorker] = None

def get_session_scanner() -> SessionScannerWorker:
    global _scanner_instance
    if _scanner_instance is None:
        _scanner_instance = SessionScannerWorker(scan_interval_seconds=45)
    return _scanner_instance

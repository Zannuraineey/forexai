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

logger = logging.getLogger("forex_ai.session_scanner")

class SessionScannerWorker:
    """
    Automated Continuous Background Session Scanner.
    Autonomously scans watchlist instruments 24/7 across Asian, London, and New York sessions.
    Evaluates institutional SMC/ICT rules (zero repainting, closed candle wicks, displacement MSS, FVG retest)
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

                # Notification config: alert on VALID_SETUP and POTENTIAL_SETUP with 15 min cooldown
                notif_config = NotificationRuleConfig(
                    notify_on_valid_setup=True,
                    notify_on_potential_setup=True,
                    notify_on_watch=False,
                    notify_on_invalidation=False,
                    cooldown_minutes=15,
                    symbols_whitelist=[],
                )
                notif_svc = NotificationService(db)
                ai_engine = AIAnalysisEngine(db)

                # Institutional execution timeframes to scan
                timeframes = ["5m", "15m"]

                for inst in instruments:
                    symbol = inst.symbol.upper()
                    for tf in timeframes:
                        try:
                            req = AIAnalysisRequest(
                                symbol=symbol,
                                timeframe=tf,
                                session_name=active_session,
                            )
                            analysis_record = await ai_engine.execute_analysis(req)

                            item_res = {
                                "symbol": symbol,
                                "timeframe": tf,
                                "session": active_session,
                                "state": analysis_record.state.value,
                                "summary": analysis_record.summary,
                                "timestamp": analysis_record.timestamp_utc.isoformat(),
                            }
                            cycle_results.append(item_res)

                            # If setup confirmed or preparing, dispatch push notification
                            if analysis_record.state in [AnalysisStateEnum.VALID_SETUP, AnalysisStateEnum.POTENTIAL_SETUP]:
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

            except Exception as exc:
                self._last_error = str(exc)
                logger.error(f"[SessionScanner] Database session error: {exc}", exc_info=True)

        self._last_results = cycle_results[-30:]
        logger.info(
            f"🔄 [SessionScanner] Cycle #{self._total_scans} completed for [{active_session.upper()}]. "
            f"Evaluated {len(cycle_results)} symbol/TF pairs, found {setups_found} active setup(s)."
        )

        return {
            "timestamp_utc": now_utc.isoformat(),
            "session": active_session,
            "scanned_count": len(cycle_results),
            "setups_found": setups_found,
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

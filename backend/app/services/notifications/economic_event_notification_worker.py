import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Set
from app.core.database import async_session_factory
from app.services.news.economic_calendar_service import EconomicCalendarService
from app.services.notifications.notification_service import NotificationService

logger = logging.getLogger("forex_ai.economic_event_worker")

class EconomicEventNotificationWorker:
    """
    Automated Background Worker for Economic News Push Notifications.
    Monitors macroeconomic calendars 24/7 to deliver:
    1. Pre-Release Urgent Alerts: Sent 10 to 5 minutes prior to High & Medium impact releases.
    2. Daily Macro Briefings: Sent once daily compiling high-impact economic catalysts for the trading day.
    """

    def __init__(self, check_interval_seconds: int = 45):
        self.check_interval_seconds = check_interval_seconds
        self._is_running = False
        self._task: Optional[asyncio.Task] = None
        self._calendar_service = EconomicCalendarService()
        self._sent_urgent_event_ids: Set[str] = set()
        self._last_briefing_date = None
        self._total_urgent_sent = 0
        self._total_briefings_sent = 0
        self._last_check_utc: Optional[datetime] = None

    async def start(self) -> None:
        """Starts the background event notification task."""
        if self._is_running:
            logger.warning("EconomicEventNotificationWorker is already running.")
            return

        self._is_running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"EconomicEventNotificationWorker started with {self.check_interval_seconds}s cycle.")

    async def stop(self) -> None:
        """Gracefully stops the worker."""
        self._is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("EconomicEventNotificationWorker stopped successfully.")

    async def _run_loop(self) -> None:
        # Initial brief settling delay
        await asyncio.sleep(5)
        while self._is_running:
            try:
                await self.check_and_dispatch_once()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in EconomicEventNotificationWorker cycle: {e}", exc_info=True)

            try:
                await asyncio.sleep(self.check_interval_seconds)
            except asyncio.CancelledError:
                break

    async def check_and_dispatch_once(self) -> Dict[str, Any]:
        """
        Executes a single evaluation pass for upcoming 10-5m releases and daily briefing.
        Can be invoked by background loop or via API for manual testing.
        """
        now = datetime.now(timezone.utc)
        self._last_check_utc = now
        urgent_dispatched = []
        daily_dispatched = False

        events = await self._calendar_service.get_all_events_async(force_refresh=False)
        if not events:
            return {"status": "NO_EVENTS", "timestamp": now.isoformat()}

        # -------------------------------------------------------------
        # 1. PRE-RELEASE URGENT ALERTS (10 to 5 Minutes Prior to Event)
        # -------------------------------------------------------------
        for ev in events:
            if ev.impact not in ["HIGH", "MEDIUM"]:
                continue

            diff_seconds = (ev.event_time_utc - now).total_seconds()
            diff_minutes = diff_seconds / 60.0

            # Window: 4.5 to 11.0 minutes remaining until release
            if 4.5 <= diff_minutes <= 11.0:
                if ev.id not in self._sent_urgent_event_ids:
                    mins_rounded = max(5, int(round(diff_minutes)))
                    try:
                        async with async_session_factory() as session:
                            notif_svc = NotificationService(session)
                            res = await notif_svc.dispatch_economic_event_alert(
                                event=ev,
                                minutes_until=mins_rounded,
                            )
                            if res:
                                self._sent_urgent_event_ids.add(ev.id)
                                self._total_urgent_sent += 1
                                urgent_dispatched.append({
                                    "event_id": ev.id,
                                    "title": ev.title,
                                    "currency": ev.currency,
                                    "impact": ev.impact,
                                    "minutes_until": mins_rounded,
                                })
                                logger.info(
                                    f"Dispatched {mins_rounded}m pre-release alert for {ev.currency} {ev.title} "
                                    f"(Release in {diff_minutes:.1f}m)."
                                )
                    except Exception as err:
                        logger.error(f"Failed to dispatch urgent alert for {ev.id}: {err}")

        # -------------------------------------------------------------
        # 2. DAILY MACRO BRIEFING (Once Per UTC Day)
        # -------------------------------------------------------------
        today_date = now.date()
        if self._last_briefing_date != today_date:
            today_events = [
                e for e in events
                if e.event_time_utc.date() == today_date and e.impact in ["HIGH", "MEDIUM"]
            ]
            if today_events:
                try:
                    async with async_session_factory() as session:
                        notif_svc = NotificationService(session)
                        res = await notif_svc.dispatch_daily_events_briefing(today_events)
                        if res:
                            self._last_briefing_date = today_date
                            self._total_briefings_sent += 1
                            daily_dispatched = True
                            logger.info(
                                f"Dispatched daily macro events briefing for {today_date} "
                                f"({len(today_events)} events)."
                            )
                except Exception as err:
                    logger.error(f"Failed to dispatch daily briefing: {err}")

        # Clean up stale IDs from tracking set (older than 6 hours)
        if len(self._sent_urgent_event_ids) > 100:
            self._sent_urgent_event_ids.clear()

        return {
            "status": "COMPLETED",
            "timestamp": now.isoformat(),
            "urgent_dispatched": urgent_dispatched,
            "daily_dispatched": daily_dispatched,
            "total_urgent_sent": self._total_urgent_sent,
            "total_briefings_sent": self._total_briefings_sent,
        }

# Global singleton
_global_event_worker: Optional[EconomicEventNotificationWorker] = None

def get_economic_event_worker() -> EconomicEventNotificationWorker:
    global _global_event_worker
    if _global_event_worker is None:
        _global_event_worker = EconomicEventNotificationWorker(check_interval_seconds=45)
    return _global_event_worker

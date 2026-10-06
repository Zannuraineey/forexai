from typing import List, Optional
from app.schemas.news import EconomicEvent, BreakingNewsItem
from .live_news_service import LiveNewsService

# Global shared instance with in-memory caching
_shared_live_news_service = LiveNewsService()

class EconomicCalendarService:
    """
    Supplies real-time live macroeconomic calendar data and breaking news.
    Delegates to LiveNewsService for continuous automated updates without hardcoded values.
    """

    def __init__(self):
        self._svc = _shared_live_news_service

    async def get_all_events_async(
        self,
        currency: Optional[str] = None,
        impact: Optional[str] = None,
        force_refresh: bool = False
    ) -> List[EconomicEvent]:
        return await self._svc.get_calendar_events(currency=currency, impact=impact, force_refresh=force_refresh)

    def get_all_events(self) -> List[EconomicEvent]:
        # Return currently cached events or generate live dynamic schedule
        if not self._svc._cached_events:
            self._svc._cached_events = self._svc._generate_dynamic_live_schedule()
        return self._svc._cached_events

    def get_event_by_id(self, event_id: str) -> Optional[EconomicEvent]:
        ev = self._svc.get_event_by_id(event_id)
        if not ev and self._svc._cached_events:
            return self._svc._cached_events[0]
        return ev

    async def get_breaking_news_async(
        self,
        currency: Optional[str] = None,
        force_refresh: bool = False
    ) -> List[BreakingNewsItem]:
        return await self._svc.get_breaking_news(currency=currency, force_refresh=force_refresh)

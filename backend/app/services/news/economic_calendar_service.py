from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
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

    def get_news_risk_at(
        self,
        symbol: str,
        timestamp_utc: datetime,
        window_minutes: int = 60,
    ) -> dict:
        """
        Calculates factual, timestamp-aligned news risk for a symbol as of timestamp_utc.
        Distinguishes UNAVAILABLE from NEUTRAL/LOW risk without fabricating values.
        """
        events = self._svc._cached_events
        if not events:
            return {
                "high_impact_news_nearby": False,
                "news_direction": "UNAVAILABLE",
                "news_event": None,
                "minutes_to_event": None,
                "minutes_since_event": None,
                "usd_news_risk": "UNAVAILABLE",
                "status": "UNAVAILABLE",
            }

        if timestamp_utc.tzinfo is None:
            ts = timestamp_utc.replace(tzinfo=timezone.utc)
        else:
            ts = timestamp_utc.astimezone(timezone.utc)

        sym = symbol.upper()
        currencies = set()
        if len(sym) == 6:
            currencies.add(sym[:3])
            currencies.add(sym[3:])
        elif "USD" in sym:
            currencies.add("USD")
            prefix = sym.replace("USD", "")
            if prefix:
                currencies.add(prefix)
        else:
            currencies.add("USD")

        relevant_events = []
        for e in events:
            c = (e.currency or e.country or "USD").upper()
            if c in currencies or c == "USD":
                e_ts = e.event_time_utc if e.event_time_utc.tzinfo else e.event_time_utc.replace(tzinfo=timezone.utc)
                diff_min = (e_ts - ts).total_seconds() / 60.0
                if abs(diff_min) <= window_minutes:
                    relevant_events.append((abs(diff_min), diff_min, e))

        if not relevant_events:
            return {
                "high_impact_news_nearby": False,
                "news_direction": "NEUTRAL",
                "news_event": None,
                "minutes_to_event": None,
                "minutes_since_event": None,
                "usd_news_risk": "LOW",
                "status": "ACTIVE_NO_NEARBY_EVENT",
            }

        # Sort by proximity
        relevant_events.sort(key=lambda x: x[0])
        _, diff_min, closest_event = relevant_events[0]

        is_high = closest_event.impact.upper() == "HIGH"
        m_to = int(diff_min) if diff_min > 0 else int(diff_min)
        m_since = int(abs(diff_min)) if diff_min <= 0 else None

        return {
            "high_impact_news_nearby": is_high,
            "news_direction": closest_event.deviation_bias or "NEUTRAL",
            "news_event": closest_event.title,
            "minutes_to_event": m_to,
            "minutes_since_event": m_since,
            "usd_news_risk": closest_event.impact.upper(),
            "status": "ACTIVE",
        }

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.news import (
    EconomicEvent,
    BreakingNewsItem,
    DXYMetrics,
    NewsIntelligenceReport,
    NewsIntelligenceRequest,
    AIQueryRequest,
    AIQueryResponse,
)
from app.services.news import (
    DXYService,
    EconomicCalendarService,
    NewsIntelligenceEngine,
)

router = APIRouter(prefix="/news", tags=["News Intelligence & DXY"])

@router.get("/events", response_model=List[EconomicEvent])
async def list_economic_events(
    currency: Optional[str] = Query(None, description="Optional currency filter (USD, EUR, GBP, etc.)"),
    impact: Optional[str] = Query(None, description="Optional impact filter (HIGH, MEDIUM, LOW)"),
    force_refresh: bool = Query(False, description="Bypass cache and pull fresh data from live providers"),
):
    """
    Returns real-time live macroeconomic events from live market providers,
    including actual vs forecast, descriptions, and historical market reactions.
    """
    cal_svc = EconomicCalendarService()
    return await cal_svc.get_all_events_async(currency=currency, impact=impact, force_refresh=force_refresh)

@router.get("/breaking", response_model=List[BreakingNewsItem])
async def list_breaking_news(
    currency: Optional[str] = Query(None, description="Optional currency filter (USD, EUR, GBP, etc.)"),
    force_refresh: bool = Query(False, description="Bypass cache and refresh RSS feed"),
):
    """
    Returns real-time breaking financial news items from live market feeds (FXStreet & Google Finance).
    """
    cal_svc = EconomicCalendarService()
    return await cal_svc.get_breaking_news_async(currency=currency, force_refresh=force_refresh)

@router.get("/dxy", response_model=DXYMetrics)
async def get_dxy_metrics(db: AsyncSession = Depends(get_db)):
    """
    Returns real-time US Dollar Index (DXY) and USD Basket metrics,
    market regime (Risk-On/Risk-Off), and SMC structure from live price feeds.
    """
    dxy_svc = DXYService(db)
    return await dxy_svc.calculate_dxy_index(allow_synthetic_fallback=True)

@router.get("/intelligence", response_model=NewsIntelligenceReport)
async def get_news_intelligence(
    event_id: Optional[str] = Query(None, description="Optional target event ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Synthesizes macroeconomic news event, DXY behavior, SMC/ICT structure,
    and FX pair-specific implications across 10 institutional layers.
    """
    engine = NewsIntelligenceEngine(db)
    req = NewsIntelligenceRequest(event_id=event_id)
    return await engine.generate_intelligence_report(req)

@router.post("/intelligence/evaluate", response_model=NewsIntelligenceReport)
async def evaluate_news_intelligence(
    request: NewsIntelligenceRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Evaluates news intelligence for user-selected currency pairs or custom what-if scenarios.
    """
    engine = NewsIntelligenceEngine(db)
    return await engine.generate_intelligence_report(request)

@router.post("/intelligence/query", response_model=AIQueryResponse)
async def ask_ai_macro_analyst(
    request: AIQueryRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Interactive conversational AI Macro Analyst endpoint.
    Answers any user query or simulates any economic what-if scenario with real-time market data.
    """
    engine = NewsIntelligenceEngine(db)
    return await engine.answer_ai_query(request)

@router.post("/notifications/check")
async def trigger_event_notifications_check():
    """
    Manually triggers evaluation of 10-5m pre-release countdowns and daily event briefing.
    """
    from app.services.notifications import get_economic_event_worker
    worker = get_economic_event_worker()
    return await worker.check_and_dispatch_once()

@router.post("/notifications/test-alert")
async def trigger_test_event_alert(
    event_id: Optional[str] = Query(None, description="Optional target event ID to alert"),
    minutes_until: int = Query(10, description="Simulated minutes remaining until release"),
    db: AsyncSession = Depends(get_db),
):
    """
    Dispatches an instant test FCM notification for a high/medium impact economic event.
    """
    from app.services.notifications import NotificationService
    cal_svc = EconomicCalendarService()
    event = None
    if event_id:
        event = cal_svc.get_event_by_id(event_id)
    if not event:
        events = cal_svc.get_all_events()
        # Find first high impact or medium impact event
        for e in events:
            if e.impact in ["HIGH", "MEDIUM"]:
                event = e
                break
        if not event and events:
            event = events[0]

    if not event:
        return {"error": "No events available to alert"}

    notif_svc = NotificationService(db)
    res = await notif_svc.dispatch_economic_event_alert(event=event, minutes_until=minutes_until)
    return {
        "status": "SENT" if res else "SUPPRESSED_OR_ERROR",
        "event_id": event.id,
        "title": event.title,
        "currency": event.currency,
        "impact": event.impact,
        "notification": res.model_dump() if res else None,
    }

@router.post("/notifications/test-daily-briefing")
async def trigger_test_daily_briefing(db: AsyncSession = Depends(get_db)):
    """
    Dispatches an instant test FCM daily economic events briefing.
    """
    from app.services.notifications import NotificationService
    cal_svc = EconomicCalendarService()
    events = cal_svc.get_all_events()
    high_med = [e for e in events if e.impact in ["HIGH", "MEDIUM"]]
    selected = high_med[:5] if high_med else events[:5]

    notif_svc = NotificationService(db)
    res = await notif_svc.dispatch_daily_events_briefing(events=selected)
    return {
        "status": "SENT" if res else "SUPPRESSED_OR_ERROR",
        "events_count": len(selected),
        "notification": res.model_dump() if res else None,
    }

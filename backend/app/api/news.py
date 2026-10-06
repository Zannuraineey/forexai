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
from app.services.news.dxy_service import DXYService
from app.services.news.economic_calendar_service import EconomicCalendarService
from app.services.news.news_intelligence_engine import NewsIntelligenceEngine

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
    return await dxy_svc.calculate_dxy_index()

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

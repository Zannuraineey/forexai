from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.news import (
    EconomicEvent,
    DXYMetrics,
    NewsIntelligenceReport,
    NewsIntelligenceRequest,
)
from app.services.news.dxy_service import DXYService
from app.services.news.economic_calendar_service import EconomicCalendarService
from app.services.news.news_intelligence_engine import NewsIntelligenceEngine

router = APIRouter(prefix="/news", tags=["News Intelligence & DXY"])

@router.get("/events", response_model=List[EconomicEvent])
async def list_economic_events():
    """
    Returns upcoming and recent high-impact macroeconomic events,
    including actual vs forecast, descriptions, and historical market reactions.
    """
    cal_svc = EconomicCalendarService()
    return cal_svc.get_all_events()

@router.get("/dxy", response_model=DXYMetrics)
async def get_dxy_metrics(db: AsyncSession = Depends(get_db)):
    """
    Returns real-time US Dollar Index (DXY) and USD Basket metrics,
    market regime (Risk-On/Risk-Off), and SMC structure.
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
    Evaluates news intelligence for user-selected currency pairs.
    """
    engine = NewsIntelligenceEngine(db)
    return await engine.generate_intelligence_report(request)

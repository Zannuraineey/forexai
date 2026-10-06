import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import get_db
from app.services.news.economic_calendar_service import EconomicCalendarService
from app.services.news.dxy_service import DXYService
from app.services.news.news_intelligence_engine import NewsIntelligenceEngine
from app.schemas.news import NewsIntelligenceRequest

@pytest.mark.asyncio
async def test_economic_calendar_service():
    service = EconomicCalendarService()
    events = service.get_all_events()
    assert len(events) >= 5
    
    first = events[0]
    assert first.id
    assert first.title
    assert first.currency
    assert first.impact in ["HIGH", "MEDIUM", "LOW"]
    assert len(first.historical_reactions) > 0
    assert any(e.currency == "USD" for e in events)

@pytest.mark.asyncio
async def test_dxy_service(db_session):
    dxy_service = DXYService(db_session)
    dxy = await dxy_service.calculate_dxy_index()
    
    assert dxy.value > 0
    assert dxy.trend in ["BULLISH", "BEARISH", "CONSOLIDATING"]
    assert dxy.market_regime in ["RISK_ON", "RISK_OFF", "NEUTRAL"]
    assert 0 <= dxy.rsi_14 <= 100
    assert dxy.ema_200 > 0
    assert isinstance(dxy.displacement_active, bool)

@pytest.mark.asyncio
async def test_news_intelligence_synthesis(db_session):
    engine = NewsIntelligenceEngine(db_session)
    req = NewsIntelligenceRequest(
        user_pairs=["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"]
    )
    report = await engine.generate_intelligence_report(req)
    
    assert report.id.startswith("rep_")
    assert report.event.title
    assert report.dxy_context.value > 0
    assert report.deviation_analysis
    assert report.historical_comparison
    assert report.macro_regime_summary
    assert report.smc_technical_synthesis
    assert len(report.pair_analyses) == 4
    assert report.actionable_conclusion
    
    eurusd = next((p for p in report.pair_analyses if p.symbol == "EURUSD"), None)
    assert eurusd is not None
    assert eurusd.correlation_to_usd == "INVERSE"
    assert eurusd.confidence > 0
    assert eurusd.trade_thesis

@pytest.mark.asyncio
async def test_news_api_endpoints(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Economic events
        res = await client.get("/api/v1/news/events")
        assert res.status_code == 200
        events = res.json()
        assert len(events) >= 5
        assert any(e["currency"] == "USD" for e in events)

        # 2. DXY metrics
        res_dxy = await client.get("/api/v1/news/dxy")
        assert res_dxy.status_code == 200
        dxy = res_dxy.json()
        assert dxy["value"] > 0
        assert "trend" in dxy
        assert "smc_structure" in dxy

        # 3. News Intelligence Report
        res_intel = await client.get("/api/v1/news/intelligence")
        assert res_intel.status_code == 200
        intel = res_intel.json()
        assert intel["id"].startswith("rep_")
        assert "macro_regime_summary" in intel
        assert len(intel["pair_analyses"]) > 0

        # 4. News Intelligence Evaluation POST
        res_post = await client.post(
            "/api/v1/news/intelligence/evaluate",
            json={
                "user_pairs": ["EURUSD", "USDJPY", "XAUUSD"],
                "custom_notes": "Testing news evaluation"
            }
        )
        assert res_post.status_code == 200
        post_intel = res_post.json()
        assert len(post_intel["pair_analyses"]) == 3

        # 5. Live Breaking News GET
        res_breaking = await client.get("/api/v1/news/breaking")
        assert res_breaking.status_code == 200
        breaking_items = res_breaking.json()
        assert isinstance(breaking_items, list)

        # 6. Interactive AI Macro Query POST
        res_query = await client.post(
            "/api/v1/news/intelligence/query",
            json={
                "query": "What happens if US Unemployment Claims spike to 230K?",
                "user_pairs": ["EURUSD", "XAUUSD"]
            }
        )
        assert res_query.status_code == 200
        query_data = res_query.json()
        assert "ai_analysis" in query_data
        assert len(query_data["key_takeaways"]) > 0
        assert len(query_data["pair_analyses"]) == 2

    app.dependency_overrides.clear()

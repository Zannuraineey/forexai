import pytest
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone
from app.main import app
from app.core.database import get_db
from app.services.candle_service import CandleService
from app.schemas.candle import CandleDTO

@pytest.mark.asyncio
async def test_health_check_endpoint(db_session):
    # Override get_db to use test db_session
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["database"]["status"] == "healthy"

    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_instruments_endpoints(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create instrument
        create_res = await client.post(
            "/api/v1/instruments",
            json={
                "symbol": "USDJPY",
                "base_asset": "USD",
                "quote_asset": "JPY",
                "pip_size": 0.01,
                "is_active": True
            }
        )
        assert create_res.status_code == 201
        created_data = create_res.json()
        assert created_data["symbol"] == "USDJPY"

        # List instruments
        list_res = await client.get("/api/v1/instruments")
        assert list_res.status_code == 200
        items = list_res.json()
        assert any(item["symbol"] == "USDJPY" for item in items)

    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_candles_query_endpoint(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)

    svc = CandleService(db_session)
    ts = datetime(2026, 10, 4, 10, 0, 0, tzinfo=timezone.utc)
    await svc.save_candles([
        CandleDTO(
            symbol="EURUSD",
            timeframe="15m",
            timestamp_utc=ts,
            open=1.0850,
            high=1.0870,
            low=1.0840,
            close=1.0860,
            volume=200.0,
            provider="mock"
        )
    ])

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/candles/EURUSD?timeframe=15m")
        assert res.status_code == 200
        candles = res.json()
        assert len(candles) >= 1
        assert candles[0]["open"] == 1.0850
        assert candles[0]["close"] == 1.0860

    app.dependency_overrides.clear()

import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import get_db
from app.schemas.candle import CandleDTO
from app.services.candle_service import CandleService
from app.services.features.context_engine import MarketContextEngine

@pytest.mark.asyncio
async def test_market_context_engine_generation(db_session):
    svc = CandleService(db_session)
    now = datetime(2026, 10, 4, 12, 0, 0, tzinfo=timezone.utc)

    # Seed 30 15m candles
    candles_15m = []
    for i in range(30):
        ts = now - timedelta(minutes=15 * (30 - i))
        price = 1.0850 + (i * 0.0002)
        candles_15m.append(
            CandleDTO(
                symbol="EURUSD",
                timeframe="15m",
                timestamp_utc=ts,
                open=price,
                high=price + 0.0005,
                low=price - 0.0003,
                close=price + 0.0001,
                volume=150.0,
                provider="mock"
            )
        )
    await svc.save_candles(candles_15m)

    # Fetch stored candles
    retrieved_15m = await svc.get_candles("EURUSD", "15m", limit=30)
    assert len(retrieved_15m) == 30

    # Generate context
    snapshot = MarketContextEngine.generate_context(
        symbol="EURUSD",
        timeframe="15m",
        candles=retrieved_15m,
        daily_candles=[],
        pip_size=0.0001
    )

    assert snapshot.symbol == "EURUSD"
    assert snapshot.timeframe == "15m"
    assert snapshot.indicators.rsi_14 is not None
    assert snapshot.indicators.atr_14 is not None
    assert snapshot.indicators.ema_9 is not None
    assert snapshot.candle_structure is not None

@pytest.mark.asyncio
async def test_market_context_api_endpoint(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    svc = CandleService(db_session)
    now = datetime(2026, 10, 4, 12, 0, 0, tzinfo=timezone.utc)

    # Seed 25 15m candles
    batch = []
    for i in range(25):
        ts = now - timedelta(minutes=15 * (25 - i))
        batch.append(
            CandleDTO(
                symbol="GBPUSD",
                timeframe="15m",
                timestamp_utc=ts,
                open=1.3000 + i * 0.0001,
                high=1.3005 + i * 0.0001,
                low=1.2995 + i * 0.0001,
                close=1.3002 + i * 0.0001,
                volume=100.0,
                provider="mock"
            )
        )
    await svc.save_candles(batch)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/context/GBPUSD?timeframe=15m")
        assert res.status_code == 200
        data = res.json()
        assert data["symbol"] == "GBPUSD"
        assert "indicators" in data
        assert "market_structure" in data
        assert "reference_levels" in data
        assert "candle_structure" in data

    app.dependency_overrides.clear()

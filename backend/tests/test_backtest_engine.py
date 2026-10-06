import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.database import get_db
from app.schemas.candle import CandleDTO
from app.schemas.backtest import BacktestRequest
from app.services.candle_service import CandleService
from app.services.backtesting import BacktestEngine

@pytest.mark.asyncio
async def test_backtest_engine_run_and_metrics(db_session):
    candle_svc = CandleService(db_session)
    start_ts = datetime(2026, 10, 1, 0, 0, 0, tzinfo=timezone.utc)
    end_ts = start_ts + timedelta(hours=10)

    # Seed 40 15m candles
    candles = []
    for i in range(40):
        ts = start_ts + timedelta(minutes=15 * i)
        price = 1.0800 + (i * 0.0002)
        candles.append(
            CandleDTO(
                symbol="EURUSD",
                timeframe="15m",
                timestamp_utc=ts,
                open=price,
                high=price + 0.0005,
                low=price - 0.0003,
                close=price + 0.0002,
                volume=100.0,
                provider="deriv",
            )
        )
    await candle_svc.save_candles(candles)

    # Seed daily candle
    await candle_svc.save_candles([
        CandleDTO(
            symbol="EURUSD",
            timeframe="1d",
            timestamp_utc=start_ts - timedelta(days=1),
            open=1.0750,
            high=1.0820,
            low=1.0740,
            close=1.0810,
            volume=5000.0,
            provider="deriv",
        )
    ])

    engine = BacktestEngine(db_session)
    req = BacktestRequest(
        symbol="EURUSD",
        timeframe="15m",
        session_name="asian",
        custom_instructions="Only consider a setup after price sweeps the Asian high.",
        start_date=start_ts + timedelta(hours=2),
        end_date=end_ts,
    )

    result = await engine.run_backtest(req, user_id=1)
    assert result.id is not None
    assert result.symbol == "EURUSD"
    assert result.total_candles_analyzed > 0
    assert result.status == "COMPLETED"
    assert isinstance(result.state_distribution, dict)

@pytest.mark.asyncio
async def test_backtest_api_endpoints(db_session):
    candle_svc = CandleService(db_session)
    start_ts = datetime(2026, 10, 1, 0, 0, 0, tzinfo=timezone.utc)
    end_ts = start_ts + timedelta(hours=6)

    # Seed 25 15m candles
    candles = [
        CandleDTO(
            symbol="EURUSD",
            timeframe="15m",
            timestamp_utc=start_ts + timedelta(minutes=15 * i),
            open=1.0850,
            high=1.0870,
            low=1.0840,
            close=1.0860,
            volume=100.0,
            provider="deriv",
        )
        for i in range(25)
    ]
    await candle_svc.save_candles(candles)

    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.post(
                "/api/v1/analysis/backtest",
                json={
                    "symbol": "EURUSD",
                    "timeframe": "15m",
                    "session_name": "london",
                    "custom_instructions": "Price above EMA 50 and RSI < 70.",
                    "start_date": (start_ts + timedelta(hours=2)).isoformat(),
                    "end_date": end_ts.isoformat(),
                }
            )
            assert res.status_code == 200
            data = res.json()
            assert "total_candles_analyzed" in data
            assert data["symbol"] == "EURUSD"
            bt_id = data["id"]

            # Query by ID
            get_res = await client.get(f"/api/v1/analysis/backtest/{bt_id}")
            assert get_res.status_code == 200
            assert get_res.json()["id"] == bt_id
    finally:
        app.dependency_overrides.clear()

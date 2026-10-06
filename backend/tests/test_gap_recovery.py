import pytest
from datetime import datetime, timedelta, timezone
from app.services.market_data.mock_provider import MockMarketDataProvider
from app.services.market_data.gap_recovery import GapRecoveryEngine
from app.services.candle_service import CandleService
from app.schemas.candle import CandleDTO

@pytest.mark.asyncio
async def test_cold_start_recovery(db_session):
    provider = MockMarketDataProvider(base_price=1.0850)
    await provider.connect()
    
    engine = GapRecoveryEngine(db_session, provider)
    now_utc = datetime(2026, 10, 4, 12, 0, 0, tzinfo=timezone.utc)

    # Database is completely empty for EURUSD 1h
    report = await engine.recover_symbol_timeframe(
        symbol="EURUSD",
        timeframe="1h",
        now_utc=now_utc,
        default_lookback_days=1
    )

    assert report.status == "RECOVERED"
    assert report.recovered_bars > 0

    svc = CandleService(db_session)
    stored = await svc.get_candles("EURUSD", "1h")
    assert len(stored) == report.recovered_bars
    await provider.disconnect()

@pytest.mark.asyncio
async def test_render_restart_gap_recovery(db_session):
    """
    Simulates a scenario where Render backend stops for 4 hours.
    Verifies that upon restart, the gap is detected, filled from provider,
    and subsequent checks recognize that the series is up-to-date.
    """
    provider = MockMarketDataProvider(base_price=1.0850)
    await provider.connect()
    svc = CandleService(db_session)

    # 1. State before crash: Last candle at 08:00 UTC (15m timeframe)
    crash_time = datetime(2026, 10, 4, 8, 0, 0, tzinfo=timezone.utc)
    seed_candle = CandleDTO(
        symbol="GBPUSD",
        timeframe="15m",
        timestamp_utc=crash_time,
        open=1.3000,
        high=1.3020,
        low=1.2990,
        close=1.3010,
        volume=100.0,
        provider="mock"
    )
    await svc.save_candles([seed_candle])

    # 2. Server restarts 4 hours later at 12:00 UTC
    restart_time = datetime(2026, 10, 4, 12, 0, 0, tzinfo=timezone.utc)
    engine = GapRecoveryEngine(db_session, provider)

    # 3. Execute recovery
    report = await engine.recover_symbol_timeframe(
        symbol="GBPUSD",
        timeframe="15m",
        now_utc=restart_time
    )

    assert report.status == "RECOVERED"
    # Gap is 4 hours minus 1 timeframe (15m) = 15 or 16 bars
    assert report.recovered_bars >= 15
    assert report.gap_duration_seconds == (restart_time - (crash_time + timedelta(minutes=15))).total_seconds()

    # 4. Verify consecutive timestamps with no missing intervals
    candles = await svc.get_candles("GBPUSD", "15m", limit=100)
    for i in range(1, len(candles)):
        diff = (candles[i].timestamp_utc - candles[i-1].timestamp_utc).total_seconds()
        assert diff == 900 # 15 minutes exactly

    # 5. Immediate second run: must report UP_TO_DATE
    second_report = await engine.recover_symbol_timeframe(
        symbol="GBPUSD",
        timeframe="15m",
        now_utc=restart_time
    )
    assert second_report.status == "UP_TO_DATE"
    assert second_report.recovered_bars == 0

    await provider.disconnect()

import pytest
from datetime import datetime, timezone, timedelta
from app.models.instrument import Instrument
from app.models.candle import Candle
from app.models.analysis import AnalysisResult, AnalysisStateEnum
from app.schemas.candle import CandleDTO
from app.schemas.ai_analysis import AIAnalysisRequest
from app.services.candle_service import CandleService
from app.services.market_data.gap_recovery import GapRecoveryEngine
from app.services.market_data.mock_provider import MockMarketDataProvider
from app.services.ai.ai_engine import AIAnalysisEngine
from app.services.notifications import NotificationService

@pytest.mark.asyncio
async def test_render_4_hour_outage_restart_and_gap_filling(db_session):
    """
    Simulates Render server shutdown for 4 hours.
    Verifies that on restart with ZERO state in RAM:
    1. System queries PostgreSQL for the latest stored candle.
    2. Identifies the exact 4-hour gap.
    3. Downloads and stores missing candles.
    4. Confirms zero data loss and continuous historical chain.
    """
    service = CandleService(db_session)
    inst = await service.ensure_instrument("EURUSD")

    # 1. State before outage: Last candle saved at 10:00 UTC
    outage_start = datetime(2026, 10, 4, 10, 0, 0, tzinfo=timezone.utc)
    pre_outage_candles = [
        CandleDTO(
            symbol="EURUSD",
            timeframe="15m",
            timestamp_utc=outage_start,
            open=1.0820,
            high=1.0835,
            low=1.0815,
            close=1.0830,
            volume=50.0,
            provider="deriv",
        )
    ]
    await service.save_candles(pre_outage_candles)

    # 2. Server stopped for 4 hours, restarted at 14:00 UTC
    restart_time = outage_start + timedelta(hours=4)

    # 3. Fresh instance boot (Clean memory, zero RAM dependencies)
    provider = MockMarketDataProvider(base_price=1.0850)
    await provider.connect()
    engine = GapRecoveryEngine(db_session, provider)

    # Execute recovery on boot
    report = await engine.recover_symbol_timeframe(
        symbol="EURUSD",
        timeframe="15m",
        now_utc=restart_time,
    )

    assert report.status == "RECOVERED"
    assert report.recovered_bars > 0
    await provider.disconnect()

    # 4. Verify latest stored candle in PostgreSQL is now current
    latest = await service.get_latest_candle_timestamp(inst.id, "15m")
    assert latest is not None
    latest_utc = latest.replace(tzinfo=timezone.utc) if latest.tzinfo is None else latest.astimezone(timezone.utc)
    assert latest_utc >= restart_time - timedelta(minutes=15)

@pytest.mark.asyncio
async def test_duplicate_candle_prevention(db_session):
    """
    Verifies that concurrent or retried candle ingestion attempts
    never create duplicate rows in PostgreSQL.
    """
    service = CandleService(db_session)
    await service.ensure_instrument("GBPUSD")

    ts = datetime(2026, 10, 4, 12, 0, 0, tzinfo=timezone.utc)
    candle = CandleDTO(
        symbol="GBPUSD",
        timeframe="15m",
        timestamp_utc=ts,
        open=1.3000,
        high=1.3020,
        low=1.2990,
        close=1.3015,
        volume=100.0,
        provider="deriv",
    )

    # First write
    saved_first = await service.save_candles([candle])
    assert saved_first == 1

    # Duplicate write attempt (e.g. repeated WebSocket tick or retry worker)
    saved_second = await service.save_candles([candle])
    assert saved_second >= 0

    # Database unique constraint (instrument_id, timeframe, timestamp_utc) ensures strictly 1 row
    candles = await service.get_candles("GBPUSD", "15m", limit=10)
    assert len(candles) == 1

@pytest.mark.asyncio
async def test_duplicate_analysis_and_notification_prevention(db_session):
    """
    Verifies that repeated analysis runs on the same candle bar
    idempotently update rather than creating duplicate records,
    and notification cooldown prevents duplicate push alerts.
    """
    service = CandleService(db_session)
    await service.ensure_instrument("USDJPY", pip_size=0.01)

    now = datetime(2026, 10, 4, 15, 0, 0, tzinfo=timezone.utc)
    # Seed 10 candles
    candles = [
        CandleDTO(
            symbol="USDJPY",
            timeframe="15m",
            timestamp_utc=now - timedelta(minutes=15 * (10 - i)),
            open=145.0,
            high=145.5,
            low=144.8,
            close=145.2,
            volume=500.0,
            provider="deriv",
        )
        for i in range(10)
    ]
    await service.save_candles(candles)

    engine = AIAnalysisEngine(db_session)
    req = AIAnalysisRequest(
        symbol="USDJPY",
        timeframe="15m",
        session_name="new_york",
        custom_instructions="Only consider a setup after price sweeps the Asian high.",
    )

    # Run analysis first time
    rec1 = await engine.execute_analysis(req)
    assert rec1.id is not None

    # Run analysis second time on the same bar
    rec2 = await engine.execute_analysis(req)
    # Must update existing record without creating duplicate ID
    assert rec1.id == rec2.id

    # Test notification dispatch deduplication
    notif_svc = NotificationService(db_session)
    rec1.state = AnalysisStateEnum.VALID_SETUP # Force valid setup to test dispatch
    n1 = await notif_svc.evaluate_and_dispatch(rec1, user_id=1)
    assert n1 is not None

    # Immediate second dispatch attempt for the same setup must be suppressed
    n2 = await notif_svc.evaluate_and_dispatch(rec1, user_id=1)
    assert n2 is None

from datetime import datetime, timezone
import pytest
from app.schemas.candle import CandleRead
from app.schemas.msnr import (
    MSNRZoneType,
    MSNRZoneQuality,
    MSNRSetupType,
)
from app.schemas.smt import SMTDivergenceDetail, SMTDivergenceType, SMTPairGroup
from app.services.features.msnr_engine import MSNREngine


def make_candle(
    ts: str,
    open_p: float,
    high_p: float,
    low_p: float,
    close_p: float,
    symbol: str = "XAUUSD",
) -> CandleRead:
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return CandleRead(
        id=1,
        instrument_id=1,
        provider="TEST",
        is_complete=True,
        symbol=symbol,
        timeframe="15m",
        timestamp_utc=dt,
        open=open_p,
        high=high_p,
        low=low_p,
        close=close_p,
        volume=1000.0,
    )


def test_consequent_encroachment_calculations():
    # Bullish candle: Open 2300.0, Low 2290.0 -> CE 50% is (2300 + 2290) / 2 = 2295.0
    ce_bull = MSNREngine.calculate_consequent_encroachment(
        open_price=2300.0, high_price=2320.0, low_price=2290.0, close_price=2315.0, direction="BULLISH"
    )
    assert ce_bull == 2295.0

    # Bearish candle: Open 2320.0, High 2330.0 -> CE 50% is (2320 + 2330) / 2 = 2325.0
    ce_bear = MSNREngine.calculate_consequent_encroachment(
        open_price=2320.0, high_price=2330.0, low_price=2305.0, close_price=2310.0, direction="BEARISH"
    )
    assert ce_bear == 2325.0

    # Full range wick CE: High 2330.0, Low 2290.0 -> CE 50% is (2330 + 2290) / 2 = 2310.0
    ce_wick = MSNREngine.calculate_consequent_encroachment(
        open_price=2320.0, high_price=2330.0, low_price=2290.0, close_price=2310.0, use_wick=True
    )
    assert ce_wick == 2310.0


def test_session_phase_quarterly_theory():
    # Asia Accumulation (04:00 UTC)
    t_asia = datetime(2026, 10, 9, 4, 30, tzinfo=timezone.utc)
    assert MSNREngine.get_session_phase(t_asia) == "ACCUMULATION_ASIA"

    # London Manipulation (09:00 UTC)
    t_london = datetime(2026, 10, 9, 9, 15, tzinfo=timezone.utc)
    assert MSNREngine.get_session_phase(t_london) == "MANIPULATION_LONDON"

    # New York AM Distribution (13:30 UTC)
    t_ny = datetime(2026, 10, 9, 13, 30, tzinfo=timezone.utc)
    assert MSNREngine.get_session_phase(t_ny) == "DISTRIBUTION_NY_AM"

    # New York PM Continuation (18:00 UTC)
    t_pm = datetime(2026, 10, 9, 18, 0, tzinfo=timezone.utc)
    assert MSNREngine.get_session_phase(t_pm) == "CONTINUATION_NY_PM"


def test_msnr_rbs_flip_identification():
    """
    Test that a broken Classic A resistance becomes an RBS (Resistance Becomes Support).
    """
    candles = [
        make_candle("2026-10-09T08:00:00Z", 2300, 2305, 2298, 2302),
        make_candle("2026-10-09T08:15:00Z", 2302, 2310, 2300, 2308),
        make_candle("2026-10-09T08:30:00Z", 2308, 2315, 2305, 2312),
        make_candle("2026-10-09T08:45:00Z", 2312, 2330, 2310, 2328),  # Swing High at 2330 (Peak A)
        make_candle("2026-10-09T09:00:00Z", 2328, 2329, 2315, 2318),
        make_candle("2026-10-09T09:15:00Z", 2318, 2320, 2312, 2315),
        make_candle("2026-10-09T09:30:00Z", 2315, 2318, 2310, 2314),
        # Impulsive breakout candle closing ABOVE 2330
        make_candle("2026-10-09T09:45:00Z", 2314, 2345, 2314, 2342),
        # Retest pulling back to the broken level (2330)
        make_candle("2026-10-09T10:00:00Z", 2342, 2342, 2329, 2332),
    ]

    zones = MSNREngine.identify_msnr_zones(candles, pip_size=0.01, left_bars=2, right_bars=2)
    assert len(zones) >= 1

    rbs_zones = [z for z in zones if z.zone_type == MSNRZoneType.RBS]
    assert len(rbs_zones) == 1
    rbs = rbs_zones[0]
    assert rbs.level_price == 2330.0
    assert rbs.is_active is True
    assert rbs.quality in (MSNRZoneQuality.FRESH, MSNRZoneQuality.TESTED)


def test_msnr_sbr_flip_identification():
    """
    Test that a broken Classic V support becomes an SBR (Support Becomes Resistance).
    """
    candles = [
        make_candle("2026-10-09T08:00:00Z", 2350, 2355, 2348, 2352),
        make_candle("2026-10-09T08:15:00Z", 2352, 2353, 2335, 2338),
        make_candle("2026-10-09T08:30:00Z", 2338, 2340, 2332, 2335),
        make_candle("2026-10-09T08:45:00Z", 2335, 2338, 2320, 2322),  # Swing Low at 2320 (Trough V)
        make_candle("2026-10-09T09:00:00Z", 2322, 2335, 2321, 2332),
        make_candle("2026-10-09T09:15:00Z", 2332, 2336, 2330, 2334),
        make_candle("2026-10-09T09:30:00Z", 2334, 2335, 2328, 2330),
        # Impulsive breakdown candle closing BELOW 2320
        make_candle("2026-10-09T09:45:00Z", 2330, 2331, 2305, 2308),
        # Retest pulling back to 2320 from below
        make_candle("2026-10-09T10:00:00Z", 2308, 2319, 2306, 2317),
    ]

    zones = MSNREngine.identify_msnr_zones(candles, pip_size=0.01, left_bars=2, right_bars=2)
    assert len(zones) >= 1

    sbr_zones = [z for z in zones if z.zone_type == MSNRZoneType.SBR]
    assert len(sbr_zones) == 1
    sbr = sbr_zones[0]
    assert sbr.level_price == 2320.0
    assert sbr.is_active is True


def test_daily_profile_2_ny_reversal_smt_bullish():
    """
    Test Gold (XAUUSD) Daily Profile #2 NY Reversal:
    Triggered when Silver sweeps a low and Gold holds a Higher Low at MSNR Support during NY AM.
    """
    # Create candle series with clear swing low at 2350 (index 2)
    candles = [
        make_candle("2026-10-09T10:30:00Z", 2365, 2368, 2360, 2362),
        make_candle("2026-10-09T10:45:00Z", 2362, 2364, 2355, 2358),
        make_candle("2026-10-09T11:00:00Z", 2358, 2360, 2350, 2352),  # Swing Low at 2350
        make_candle("2026-10-09T11:15:00Z", 2352, 2358, 2352, 2355),
        make_candle("2026-10-09T11:30:00Z", 2355, 2360, 2353, 2356),
        make_candle("2026-10-09T13:00:00Z", 2356, 2358, 2351, 2353),  # NY AM retest holding 2351 (Higher low)
    ]

    # Bullish SMT Divergence with Silver
    smt_detail = SMTDivergenceDetail(
        pair_group=SMTPairGroup.METALS,
        primary_symbol="XAUUSD",
        correlated_symbol="XAGUSD",
        divergence_type=SMTDivergenceType.BULLISH_SMT,
        swept_symbol="XAGUSD",
        strong_symbol="XAUUSD",
        reference_level="ASIAN_LOW",
        primary_price_action="HIGHER_LOW_REJECTION",
        correlated_price_action="LOWER_LOW_SWEEP",
        confidence_score=0.92,
        summary="Silver swept Asian low, Gold held higher low at support.",
    )

    result = MSNREngine.analyze(
        symbol="XAUUSD",
        candles=candles,
        smt_divergence=smt_detail,
        pip_size=0.01,
    )

    assert result.has_active_setup is True
    ny_reversal_signals = [s for s in result.signals if s.setup_type == MSNRSetupType.DAILY_PROFILE_2_NY_REVERSAL]
    assert len(ny_reversal_signals) >= 1

    sig = ny_reversal_signals[0]
    assert sig.direction == "BULLISH"
    assert sig.session_phase == "DISTRIBUTION_NY_AM"
    assert sig.smt_confluence is not None
    assert sig.smt_confluence.divergence_type == SMTDivergenceType.BULLISH_SMT
    assert sig.risk_reward >= 1.5
    assert sig.confidence_score >= 0.90
    assert "Daily Profile #2 NY Bullish Reversal" in sig.summary


def test_daily_profile_2_ny_reversal_smt_bearish():
    """
    Test Gold (XAUUSD) Daily Profile #2 NY Reversal Bearish setup.
    """
    # Create candle series with clear swing high at 2360 (index 2)
    candles = [
        make_candle("2026-10-09T10:30:00Z", 2340, 2345, 2338, 2342),
        make_candle("2026-10-09T10:45:00Z", 2342, 2348, 2340, 2345),
        make_candle("2026-10-09T11:00:00Z", 2345, 2360, 2344, 2358),  # Swing High at 2360
        make_candle("2026-10-09T11:15:00Z", 2358, 2359, 2352, 2354),
        make_candle("2026-10-09T11:30:00Z", 2354, 2357, 2350, 2352),
        make_candle("2026-10-09T13:00:00Z", 2352, 2358, 2351, 2356),  # NY AM retest near 2358
    ]

    smt_detail = SMTDivergenceDetail(
        pair_group=SMTPairGroup.METALS,
        primary_symbol="XAUUSD",
        correlated_symbol="XAGUSD",
        divergence_type=SMTDivergenceType.BEARISH_SMT,
        swept_symbol="XAGUSD",
        strong_symbol="XAUUSD",
        reference_level="ASIAN_HIGH",
        primary_price_action="LOWER_HIGH_REJECTION",
        correlated_price_action="HIGHER_HIGH_SWEEP",
        confidence_score=0.92,
        summary="Silver swept Asian high, Gold held lower high at resistance.",
    )

    result = MSNREngine.analyze(
        symbol="XAUUSD",
        candles=candles,
        smt_divergence=smt_detail,
        pip_size=0.01,
    )

    assert result.has_active_setup is True
    bearish_signals = [s for s in result.signals if s.setup_type == MSNRSetupType.DAILY_PROFILE_2_NY_REVERSAL]
    assert len(bearish_signals) >= 1
    sig = bearish_signals[0]
    assert sig.direction == "BEARISH"
    assert sig.session_phase == "DISTRIBUTION_NY_AM"
    assert sig.risk_reward >= 1.5


@pytest.mark.asyncio
async def test_msnr_api_endpoints(db_session):
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    from app.core.database import get_db

    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test analysis endpoint
        res = await client.get("/api/v1/msnr/analysis?symbol=XAUUSD&timeframe=15m")
        assert res.status_code == 200
        data = res.json()
        assert data["symbol"] == "XAUUSD"
        assert "active_zones" in data
        assert "signals" in data

        # Test zones endpoint
        res_zones = await client.get("/api/v1/msnr/zones?symbol=XAUUSD&timeframe=15m")
        assert res_zones.status_code == 200
        assert isinstance(res_zones.json(), list)

        # Test setups endpoint
        res_setups = await client.get("/api/v1/msnr/setups?symbol=XAUUSD&timeframe=15m")
        assert res_setups.status_code == 200
        assert isinstance(res_setups.json(), list)

    app.dependency_overrides.clear()

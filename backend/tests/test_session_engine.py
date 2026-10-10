from datetime import datetime, timezone
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.session import SessionEngine
from app.schemas.candle import CandleRead

def test_asian_session_evaluation():
    # Asian session: 09:00 - 18:00 JST (00:00 - 09:00 UTC)
    # At 03:00 UTC, Asian should be ACTIVE
    dt_active = datetime(2026, 4, 15, 3, 0, 0, tzinfo=timezone.utc)
    res_active = SessionEngine.evaluate_sessions(dt_active)
    assert "asian" in res_active.active_sessions
    assert res_active.session_windows["asian"].is_active is True

    # At 10:00 UTC, Asian should be COMPLETED
    dt_inactive = datetime(2026, 4, 15, 10, 0, 0, tzinfo=timezone.utc)
    res_inactive = SessionEngine.evaluate_sessions(dt_inactive)
    assert "asian" not in res_inactive.active_sessions
    assert res_inactive.session_windows["asian"].status == "COMPLETED"

def test_london_dst_transitions():
    # London winter (GMT, UTC+0): 08:00 - 16:30 local time
    # 07:30 UTC on Jan 15 -> 07:30 GMT -> UPCOMING
    winter_before = datetime(2026, 1, 15, 7, 30, 0, tzinfo=timezone.utc)
    res_winter_before = SessionEngine.evaluate_sessions(winter_before)
    assert "london" not in res_winter_before.active_sessions
    assert res_winter_before.session_windows["london"].status == "UPCOMING"

    # 08:30 UTC on Jan 15 -> 08:30 GMT -> ACTIVE
    winter_during = datetime(2026, 1, 15, 8, 30, 0, tzinfo=timezone.utc)
    res_winter_during = SessionEngine.evaluate_sessions(winter_during)
    assert "london" in res_winter_during.active_sessions

    # London summer (BST, UTC+1): 08:00 - 16:30 local time is 07:00 - 15:30 UTC
    # 07:30 UTC on July 15 -> 08:30 BST -> ACTIVE!
    summer_during = datetime(2026, 7, 15, 7, 30, 0, tzinfo=timezone.utc)
    res_summer_during = SessionEngine.evaluate_sessions(summer_during)
    assert "london" in res_summer_during.active_sessions

    # 16:00 UTC on July 15 -> 17:00 BST -> COMPLETED
    summer_after = datetime(2026, 7, 15, 16, 0, 0, tzinfo=timezone.utc)
    res_summer_after = SessionEngine.evaluate_sessions(summer_after)
    assert "london" not in res_summer_after.active_sessions
    assert res_summer_after.session_windows["london"].status == "COMPLETED"

def test_new_york_dst_transitions():
    # New York winter (EST, UTC-5): 08:00 - 17:00 local time is 13:00 - 22:00 UTC
    # 12:30 UTC on Jan 15 -> 07:30 EST -> UPCOMING
    winter_before = datetime(2026, 1, 15, 12, 30, 0, tzinfo=timezone.utc)
    res_wb = SessionEngine.evaluate_sessions(winter_before)
    assert "new_york" not in res_wb.active_sessions

    # 13:30 UTC on Jan 15 -> 08:30 EST -> ACTIVE
    winter_during = datetime(2026, 1, 15, 13, 30, 0, tzinfo=timezone.utc)
    res_wd = SessionEngine.evaluate_sessions(winter_during)
    assert "new_york" in res_wd.active_sessions

    # New York summer (EDT, UTC-4): 08:00 - 17:00 local time is 12:00 - 21:00 UTC
    # 12:30 UTC on July 15 -> 08:30 EDT -> ACTIVE!
    summer_during = datetime(2026, 7, 15, 12, 30, 0, tzinfo=timezone.utc)
    res_sd = SessionEngine.evaluate_sessions(summer_during)
    assert "new_york" in res_sd.active_sessions

def test_london_new_york_overlap():
    # In Summer (July 15), London (07:00 - 15:30 UTC) and NY (12:00 - 21:00 UTC)
    # At 13:30 UTC, both London and New York should be ACTIVE -> Overlap
    dt_overlap = datetime(2026, 7, 15, 13, 30, 0, tzinfo=timezone.utc)
    res = SessionEngine.evaluate_sessions(dt_overlap)
    assert res.is_overlap is True
    assert "london" in res.active_sessions
    assert "new_york" in res.active_sessions
    assert res.overlap_name == "london_new_york_overlap"

def test_session_levels_and_asian_sweep_detection():
    # Create intraday 15m candles during Asian session (00:00 to 09:00 UTC)
    candles = []
    base_ts = datetime(2026, 10, 4, 1, 0, 0, tzinfo=timezone.utc)
    # Asian range: high 1.0850, low 1.0810
    candles.append(CandleRead(
        id=1, instrument_id=1, provider="deriv",
        symbol="EURUSD", timeframe="15m", timestamp_utc=base_ts,
        open=1.0820, high=1.0850, low=1.0810, close=1.0840, volume=100.0, is_complete=True
    ))

    # Current candle is London session (10:00 UTC)
    current_ts = datetime(2026, 10, 4, 10, 0, 0, tzinfo=timezone.utc)
    # Sweeps Asian high: High 1.0860 > 1.0850, close 1.0845
    london_candle = CandleRead(
        id=2, instrument_id=1, provider="deriv",
        symbol="EURUSD", timeframe="15m", timestamp_utc=current_ts,
        open=1.0840, high=1.0860, low=1.0835, close=1.0845, volume=200.0, is_complete=True
    )
    all_candles = candles + [london_candle]

    state = SessionEngine.evaluate_sessions(
        dt_utc=current_ts,
        candles_today=all_candles,
        pip_size=0.0001,
        current_candle=london_candle,
    )

    asian_lvl = state.session_levels["asian"]
    assert asian_lvl.high == 1.0850
    assert asian_lvl.low == 1.0810
    assert asian_lvl.swept_high is True
    assert asian_lvl.swept_low is False
    assert asian_lvl.range_pips == 40.0

@pytest.mark.asyncio
async def test_session_api_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Current session
        res = await client.get("/api/v1/sessions/current")
        assert res.status_code == 200
        data = res.json()
        assert "active_sessions" in data
        assert "session_windows" in data
        assert "asian" in data["session_windows"]
        assert "london" in data["session_windows"]
        assert "new_york" in data["session_windows"]

        # 2. Evaluate specific UTC timestamp
        eval_res = await client.get(
            "/api/v1/sessions/evaluate",
            params={"timestamp_utc": "2026-07-15T14:00:00Z"}
        )
        assert eval_res.status_code == 200
        eval_data = eval_res.json()
        assert eval_data["is_overlap"] is True
        assert "london" in eval_data["active_sessions"]
        assert "new_york" in eval_data["active_sessions"]


def test_36h_synthetic_candles_levels_persisting():
    """Feed 36 hours of synthetic 5m candles into session_engine. At 13:00 UTC, assert asian.high, asian.low, london.high are all non-null."""
    from datetime import timedelta
    current_ts = datetime(2026, 10, 5, 13, 0, 0, tzinfo=timezone.utc)
    # 36 hours of 5m candles: 36 * 12 = 432 candles
    candles = []
    start_ts = current_ts - timedelta(hours=36)
    curr = start_ts
    cid = 1
    while curr <= current_ts:
        # Base price around 1.0850 with small oscillations
        price = 1.0850 + ((cid % 20) * 0.0005)
        candles.append(CandleRead(
            id=cid,
            instrument_id=1,
            provider="deriv",
            symbol="EURUSD",
            timeframe="5m",
            timestamp_utc=curr,
            open=price,
            high=price + 0.0010,
            low=price - 0.0010,
            close=price + 0.0002,
            volume=50.0,
            is_complete=True,
        ))
        curr += timedelta(minutes=5)
        cid += 1

    state = SessionEngine.evaluate_sessions(
        dt_utc=current_ts,
        candles_today=candles,
        pip_size=0.0001,
        current_candle=candles[-1],
    )

    assert "asian" in state.session_levels
    assert state.session_levels["asian"].high is not None
    assert state.session_levels["asian"].low is not None
    assert "london" in state.session_levels
    assert state.session_levels["london"].high is not None


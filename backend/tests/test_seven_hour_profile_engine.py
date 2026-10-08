import pytest
import ast
from datetime import datetime, date, time, timedelta, timezone
from zoneinfo import ZoneInfo
from sqlalchemy import select

from app.schemas.candle import CandleDTO, CandleRead
from app.schemas.seven_hour_profile import (
    SevenHourProfileConfig,
    SevenHourProfileResult,
    ProfileStatus,
    ProfileDirection,
    ProfileClassification,
    DataQuality,
)
from app.models.seven_hour_profile import SevenHourProfile
from app.models.instrument import Instrument
from app.services.profiling.seven_hour_profile_engine import SevenHourProfileEngine
from app.services.session.session_engine import SessionEngine


def create_candle(
    timestamp: datetime,
    open_: float,
    high: float,
    low: float,
    close: float,
    timeframe: str = "1h",
    symbol: str = "EURUSD",
    instrument_id: int = 1,
    id_: int = 1,
) -> CandleRead:
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return CandleRead(
        id=id_,
        instrument_id=instrument_id,
        timeframe=timeframe,
        timestamp_utc=timestamp,
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=100.0,
        provider="deriv",
        is_complete=True,
    )


# 1. Correct 7H aggregation & 2. Correct OHLC
def test_1_and_2_correct_7h_aggregation_and_ohlc():
    """Verify that 7 consecutive 1h candles aggregate into single 7H profile with exact OHLC."""
    cfg = SevenHourProfileConfig(
        anchor_timezone="UTC",
        anchor_start=time(0, 0),
        duration_hours=7,
        source_timeframe="1h",
    )
    start_dt = datetime(2026, 10, 5, 0, 0, tzinfo=timezone.utc)
    candles = [
        create_candle(start_dt + timedelta(hours=0), 1.1000, 1.1020, 1.0990, 1.1015, id_=1),
        create_candle(start_dt + timedelta(hours=1), 1.1015, 1.1040, 1.1010, 1.1030, id_=2),
        create_candle(start_dt + timedelta(hours=2), 1.1030, 1.1055, 1.1025, 1.1045, id_=3),
        create_candle(start_dt + timedelta(hours=3), 1.1045, 1.1060, 1.1035, 1.1050, id_=4),
        create_candle(start_dt + timedelta(hours=4), 1.1050, 1.1052, 1.0980, 1.1020, id_=5), # absolute low 1.0980
        create_candle(start_dt + timedelta(hours=5), 1.1020, 1.1070, 1.1010, 1.1065, id_=6), # absolute high 1.1070
        create_candle(start_dt + timedelta(hours=6), 1.1065, 1.1068, 1.1040, 1.1060, id_=7), # close 1.1060
    ]

    end_dt = start_dt + timedelta(hours=7)
    res = SevenHourProfileEngine.build_synthetic_profile(
        symbol="EURUSD",
        window_start_utc=start_dt,
        window_end_utc=end_dt,
        candles_in_window=candles,
        config=cfg,
        current_time_utc=end_dt,
    )

    assert res.status == ProfileStatus.COMPLETED
    assert res.open == 1.1000
    assert res.high == 1.1070
    assert res.low == 1.0980
    assert res.close == 1.1060
    assert res.source_candle_count == 7
    assert res.expected_candle_count == 7
    assert res.data_quality == DataQuality.COMPLETE


# 3. Correct range / body & safe zero-range handling
def test_3_correct_range_body_wick_metrics():
    """Verify range, body, wicks, body ratio, and safe zero-range handling."""
    cfg = SevenHourProfileConfig()
    start_dt = datetime(2026, 10, 5, 0, 0, tzinfo=timezone.utc)
    end_dt = start_dt + timedelta(hours=7)

    # Bullish candle
    c1 = create_candle(start_dt, open_=1.1000, high=1.1050, low=1.0980, close=1.1040)
    res = SevenHourProfileEngine.build_synthetic_profile(
        symbol="EURUSD",
        window_start_utc=start_dt,
        window_end_utc=end_dt,
        candles_in_window=[c1],
        config=cfg,
        current_time_utc=end_dt,
    )
    assert res.range == pytest.approx(0.0070, abs=1e-6)
    assert res.body == pytest.approx(0.0040, abs=1e-6)
    assert res.features.upper_wick == pytest.approx(0.0010, abs=1e-6) # 1.1050 - 1.1040
    assert res.features.lower_wick == pytest.approx(0.0020, abs=1e-6) # 1.1000 - 1.0980
    assert res.body_ratio == pytest.approx(0.0040 / 0.0070, abs=1e-3)
    assert res.close_location == pytest.approx((1.1040 - 1.0980) / 0.0070, abs=1e-3)

    # Zero range candle (open == high == low == close)
    c_flat = create_candle(start_dt, open_=1.1000, high=1.1000, low=1.1000, close=1.1000)
    res_flat = SevenHourProfileEngine.build_synthetic_profile(
        symbol="EURUSD",
        window_start_utc=start_dt,
        window_end_utc=end_dt,
        candles_in_window=[c_flat],
        config=cfg,
        current_time_utc=end_dt,
    )
    assert res_flat.range == 0.0
    assert res_flat.body == 0.0
    assert res_flat.body_ratio == 0.0
    assert res_flat.close_location == 0.5


# 4. Correct direction
def test_4_correct_direction():
    cfg = SevenHourProfileConfig()
    start_dt = datetime(2026, 10, 5, 0, 0, tzinfo=timezone.utc)
    end_dt = start_dt + timedelta(hours=7)

    c_bull = [create_candle(start_dt, 1.1000, 1.1050, 1.0990, 1.1020)]
    res_bull = SevenHourProfileEngine.build_synthetic_profile("EURUSD", start_dt, end_dt, c_bull, cfg, current_time_utc=end_dt)
    assert res_bull.direction == ProfileDirection.BULLISH

    c_bear = [create_candle(start_dt, 1.1020, 1.1050, 1.0990, 1.1000)]
    res_bear = SevenHourProfileEngine.build_synthetic_profile("EURUSD", start_dt, end_dt, c_bear, cfg, current_time_utc=end_dt)
    assert res_bear.direction == ProfileDirection.BEARISH

    c_doji = [create_candle(start_dt, 1.1000, 1.1050, 1.0990, 1.1000)]
    res_doji = SevenHourProfileEngine.build_synthetic_profile("EURUSD", start_dt, end_dt, c_doji, cfg, current_time_utc=end_dt)
    assert res_doji.direction == ProfileDirection.NEUTRAL


# 5. Correct previous-profile comparison
def test_5_previous_profile_comparison():
    cfg = SevenHourProfileConfig()
    t1_start = datetime(2026, 10, 5, 0, 0, tzinfo=timezone.utc)
    t1_end = t1_start + timedelta(hours=7)
    t2_start = t1_end
    t2_end = t2_start + timedelta(hours=7)

    c_p1 = [create_candle(t1_start, 1.1000, 1.1050, 1.0950, 1.1020)]
    p1 = SevenHourProfileEngine.build_synthetic_profile("EURUSD", t1_start, t1_end, c_p1, cfg, current_time_utc=t1_end)

    c_p2 = [create_candle(t2_start, 1.1010, 1.1060, 1.0990, 1.1040)]
    p2 = SevenHourProfileEngine.build_synthetic_profile("EURUSD", t2_start, t2_end, c_p2, cfg, current_time_utc=t2_end, previous_profile=p1)

    assert p2.relationship is not None
    assert p2.relationship.previous_high == 1.1050
    assert p2.relationship.previous_low == 1.0950
    assert p2.relationship.previous_range == pytest.approx(0.0100, abs=1e-6)
    assert p2.relationship.open_inside_previous_range is True
    assert p2.relationship.took_previous_high is True
    assert p2.relationship.took_previous_low is False


# 6. High sweep & 7. Low sweep
def test_6_and_7_high_and_low_sweeps():
    cfg = SevenHourProfileConfig()
    t1_start = datetime(2026, 10, 5, 0, 0, tzinfo=timezone.utc)
    t1_end = t1_start + timedelta(hours=7)
    t2_start = t1_end
    t2_end = t2_start + timedelta(hours=7)

    p1 = SevenHourProfileEngine.build_synthetic_profile(
        "EURUSD", t1_start, t1_end, [create_candle(t1_start, 1.1000, 1.1050, 1.0950, 1.1000)], cfg, current_time_utc=t1_end
    )

    # High sweep: took high (1.1060 > 1.1050), but did not take low
    c_sweep_high = [create_candle(t2_start, 1.1000, 1.1060, 1.0960, 1.0990)]
    p_high_sweep = SevenHourProfileEngine.build_synthetic_profile(
        "EURUSD", t2_start, t2_end, c_sweep_high, cfg, current_time_utc=t2_end, previous_profile=p1
    )
    assert p_high_sweep.relationship.took_previous_high is True
    assert p_high_sweep.relationship.took_previous_low is False

    # Low sweep: took low (1.0940 < 1.0950), but did not take high
    c_sweep_low = [create_candle(t2_start, 1.1000, 1.1040, 1.0940, 1.1010)]
    p_low_sweep = SevenHourProfileEngine.build_synthetic_profile(
        "EURUSD", t2_start, t2_end, c_sweep_low, cfg, current_time_utc=t2_end, previous_profile=p1
    )
    assert p_low_sweep.relationship.took_previous_high is False
    assert p_low_sweep.relationship.took_previous_low is True


# 8. Expansion & 9. Contraction
def test_8_and_9_expansion_and_contraction():
    cfg = SevenHourProfileConfig()
    t1_start = datetime(2026, 10, 5, 0, 0, tzinfo=timezone.utc)
    t1_end = t1_start + timedelta(hours=7)
    t2_start = t1_end
    t2_end = t2_start + timedelta(hours=7)

    # Base profile range = 0.0100 (1.1050 - 1.0950)
    p1 = SevenHourProfileEngine.build_synthetic_profile(
        "EURUSD", t1_start, t1_end, [create_candle(t1_start, 1.1000, 1.1050, 1.0950, 1.1020)], cfg, current_time_utc=t1_end
    )

    # Expansion: range 0.0200 (1.1150 - 1.0950), closed above high
    c_expand = [create_candle(t2_start, 1.1020, 1.1150, 1.1010, 1.1120)]
    p_exp = SevenHourProfileEngine.build_synthetic_profile(
        "EURUSD", t2_start, t2_end, c_expand, cfg, current_time_utc=t2_end, previous_profile=p1
    )
    assert p_exp.relationship.expanded_vs_previous is True
    assert p_exp.relationship.contracted_vs_previous is False
    assert p_exp.relationship.expansion_ratio > 1.0
    assert p_exp.classification == ProfileClassification.BULLISH_EXPANSION

    # Contraction: range 0.0040 (1.1030 - 1.0990) inside previous range
    c_contract = [create_candle(t2_start, 1.1010, 1.1030, 1.0990, 1.1015)]
    p_cnt = SevenHourProfileEngine.build_synthetic_profile(
        "EURUSD", t2_start, t2_end, c_contract, cfg, current_time_utc=t2_end, previous_profile=p1
    )
    assert p_cnt.relationship.expanded_vs_previous is False
    assert p_cnt.relationship.contracted_vs_previous is True
    assert p_cnt.relationship.expansion_ratio < 1.0
    assert p_cnt.classification == ProfileClassification.RANGE_CONSOLIDATION


# 10. Reversal & Failed Expansion
def test_10_reversal_and_failed_expansion():
    cfg = SevenHourProfileConfig()
    t1_start = datetime(2026, 10, 5, 0, 0, tzinfo=timezone.utc)
    t1_end = t1_start + timedelta(hours=7)
    t2_start = t1_end
    t2_end = t2_start + timedelta(hours=7)

    # p1 is Bearish: open 1.1050, close 1.0960, high 1.1050, low 1.0950
    p1 = SevenHourProfileEngine.build_synthetic_profile(
        "EURUSD", t1_start, t1_end, [create_candle(t1_start, 1.1050, 1.1050, 1.0950, 1.0960)], cfg, current_time_utc=t1_end
    )

    # Bullish Reversal: swept low 1.0940 < 1.0950, but reversed and closed bullish at 1.1020 > 1.0960
    c_rev = [create_candle(t2_start, 1.0950, 1.1030, 1.0940, 1.1020)]
    p_rev = SevenHourProfileEngine.build_synthetic_profile(
        "EURUSD", t2_start, t2_end, c_rev, cfg, current_time_utc=t2_end, previous_profile=p1
    )
    assert p_rev.classification == ProfileClassification.BULLISH_REVERSAL

    # Failed Bullish Expansion: swept high 1.1040 > 1.1020, but failed to close above high (closed 1.1015)
    p_bull = SevenHourProfileEngine.build_synthetic_profile(
        "EURUSD", t1_start, t1_end, [create_candle(t1_start, 1.0960, 1.1020, 1.0950, 1.1010)], cfg, current_time_utc=t1_end
    )
    c_fail = [create_candle(t2_start, 1.1010, 1.1040, 1.0990, 1.1015)]
    p_fail = SevenHourProfileEngine.build_synthetic_profile(
        "EURUSD", t2_start, t2_end, c_fail, cfg, current_time_utc=t2_end, previous_profile=p_bull
    )
    assert p_fail.classification == ProfileClassification.FAILED_BULLISH_EXPANSION


# 11. Current incomplete profile is not confirmed
def test_11_current_incomplete_profile_status():
    cfg = SevenHourProfileConfig()
    w_start = datetime(2026, 10, 5, 0, 0, tzinfo=timezone.utc)
    w_end = w_start + timedelta(hours=7)

    # Evaluation time is only 2 hours into the 7-hour block
    eval_time = w_start + timedelta(hours=2)
    candles = [
        create_candle(w_start + timedelta(hours=0), 1.1000, 1.1020, 1.0990, 1.1010),
        create_candle(w_start + timedelta(hours=1), 1.1010, 1.1030, 1.1000, 1.1025),
    ]

    res = SevenHourProfileEngine.build_synthetic_profile(
        "EURUSD", w_start, w_end, candles, cfg, current_time_utc=eval_time
    )

    assert res.status == ProfileStatus.IN_PROGRESS
    assert res.status != ProfileStatus.COMPLETED


# 12. Completed profile never uses future candles (zero-repainting)
def test_12_completed_profile_never_uses_future_candles():
    cfg = SevenHourProfileConfig(alignment_mode="DAILY_ANCHOR")
    start_dt = datetime(2026, 10, 5, 0, 0, tzinfo=timezone.utc)
    all_candles = [
        # Window 1 (00:00 to 07:00)
        create_candle(start_dt + timedelta(hours=i), 1.1000 + i*0.001, 1.1010 + i*0.001, 1.0990 + i*0.001, 1.1005 + i*0.001, id_=i+1)
        for i in range(7)
    ]
    # Future candles in Window 2 (07:00 to 14:00) with extreme spikes
    all_candles.extend([
        create_candle(start_dt + timedelta(hours=7 + i), 1.2000, 1.2500, 1.1500, 1.2200, id_=8+i)
        for i in range(7)
    ])

    profiles = SevenHourProfileEngine.evaluate_candles(
        symbol="EURUSD",
        candles=all_candles,
        config=cfg,
        current_time_utc=start_dt + timedelta(hours=14),
    )

    assert len(profiles) >= 2
    p1 = profiles[0]
    # Profile 1 must only contain candles from 00:00 to 07:00, completely unaffected by future Window 2 spike
    assert p1.high < 1.1500
    assert p1.profile_end == start_dt + timedelta(hours=7)
    assert p1.source_candle_count == 7


# 13. Missing source candles are detected
def test_13_missing_source_candles_data_quality():
    cfg = SevenHourProfileConfig(source_timeframe="1h", duration_hours=7)
    start_dt = datetime(2026, 10, 5, 0, 0, tzinfo=timezone.utc)
    end_dt = start_dt + timedelta(hours=7)

    # 3 candles instead of expected 7
    partial_candles = [
        create_candle(start_dt + timedelta(hours=0), 1.1000, 1.1020, 1.0990, 1.1010),
        create_candle(start_dt + timedelta(hours=1), 1.1010, 1.1030, 1.1000, 1.1020),
        create_candle(start_dt + timedelta(hours=2), 1.1020, 1.1040, 1.1010, 1.1030),
    ]

    res = SevenHourProfileEngine.build_synthetic_profile(
        "EURUSD", start_dt, end_dt, partial_candles, cfg, current_time_utc=end_dt
    )
    assert res.data_quality == DataQuality.PARTIAL
    assert res.source_candle_count == 3
    assert res.expected_candle_count == 7

    # 0 candles
    res_empty = SevenHourProfileEngine.build_synthetic_profile(
        "EURUSD", start_dt, end_dt, [], cfg, current_time_utc=end_dt
    )
    assert res_empty.data_quality == DataQuality.INSUFFICIENT
    assert res_empty.classification == ProfileClassification.INSUFFICIENT_DATA


# 14. Duplicate profile prevention in DB
@pytest.mark.asyncio
async def test_14_duplicate_profile_prevention(db_session):
    inst_stmt = select(Instrument).where(Instrument.symbol == "EURUSD")
    res = await db_session.execute(inst_stmt)
    inst = res.scalar_one_or_none()
    if not inst:
        inst = Instrument(symbol="EURUSD", base_asset="EUR", quote_asset="USD", pip_size=0.0001, is_active=True)
        db_session.add(inst)
        await db_session.commit()
        await db_session.refresh(inst)

    cfg = SevenHourProfileConfig(config_id="TEST_CONFIG_14")
    start_dt = datetime(2026, 10, 5, 0, 0, tzinfo=timezone.utc)
    end_dt = start_dt + timedelta(hours=7)
    candles = [create_candle(start_dt, 1.1000, 1.1050, 1.0950, 1.1020, instrument_id=inst.id)]

    profile = SevenHourProfileEngine.build_synthetic_profile("EURUSD", start_dt, end_dt, candles, cfg, current_time_utc=end_dt)

    # First persist
    saved1 = await SevenHourProfileEngine.persist_profile(db_session, profile, inst.id)
    assert saved1.id is not None

    # Duplicate persist attempt
    saved2 = await SevenHourProfileEngine.persist_profile(db_session, profile, inst.id)
    assert saved2.id == saved1.id

    # Verify strictly 1 row in DB
    query = select(SevenHourProfile).where(
        SevenHourProfile.instrument_id == inst.id,
        SevenHourProfile.config_id == cfg.config_id,
        SevenHourProfile.profile_start_utc == start_dt,
    )
    all_rows = (await db_session.execute(query)).scalars().all()
    assert len(all_rows) == 1


# 15. Timestamp / timezone handling
def test_15_timestamp_and_timezone_handling():
    cfg = SevenHourProfileConfig(anchor_timezone="UTC", anchor_start=time(0, 0), alignment_mode="DAILY_ANCHOR")
    ts_naive = datetime(2026, 10, 5, 3, 30) # naive
    w_start, w_end = SevenHourProfileEngine.get_window_for_timestamp(ts_naive, cfg)

    assert w_start.tzinfo is not None
    assert w_end.tzinfo is not None
    assert w_start == datetime(2026, 10, 5, 0, 0, tzinfo=timezone.utc)
    assert w_end == datetime(2026, 10, 5, 7, 0, tzinfo=timezone.utc)


# 16. DST-safe anchor conversion where applicable
def test_16_dst_safe_anchor_conversion():
    """Verify window generation when anchor is in America/New_York across DST shift."""
    cfg = SevenHourProfileConfig(
        anchor_timezone="America/New_York",
        anchor_start=time(17, 0), # 17:00 NY
        duration_hours=7,
        config_id="NY_1700_7H",
        alignment_mode="DAILY_ANCHOR",
    )
    # Winter EST (UTC-5): 17:00 NY -> 22:00 UTC
    winter_date = datetime(2026, 1, 15, 17, 30, tzinfo=ZoneInfo("America/New_York"))
    w_start_winter, w_end_winter = SevenHourProfileEngine.get_window_for_timestamp(winter_date, cfg)
    assert w_start_winter.astimezone(timezone.utc).hour == 22

    # Summer EDT (UTC-4): 17:00 NY -> 21:00 UTC
    summer_date = datetime(2026, 7, 15, 17, 30, tzinfo=ZoneInfo("America/New_York"))
    w_start_summer, w_end_summer = SevenHourProfileEngine.get_window_for_timestamp(summer_date, cfg)
    assert w_start_summer.astimezone(timezone.utc).hour == 21


# 17. No dependency on SessionEngine
def test_17_no_dependency_on_session_engine():
    import app.services.profiling.seven_hour_profile_engine as engine_module
    
    # Check that SessionEngine is not in module globals or imported
    assert "SessionEngine" not in dir(engine_module)
    with open(engine_module.__file__, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())
    
    # Check that no import statement imports from session_engine or mentions SessionEngine
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "session_engine" not in alias.name
                assert "SessionEngine" not in alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                assert "session_engine" not in node.module
            for alias in node.names:
                assert "SessionEngine" not in alias.name


# 18. Changing SessionEngine session times does not change 7H profile boundaries
def test_18_changing_session_engine_does_not_affect_7h_boundaries():
    cfg = SevenHourProfileConfig(anchor_timezone="UTC", anchor_start=time(0, 0), duration_hours=7)
    sample_dt = datetime(2026, 10, 5, 10, 0, tzinfo=timezone.utc)

    # Initial 7H window
    w1_start, w1_end = SevenHourProfileEngine.get_window_for_timestamp(sample_dt, cfg)

    # Mutate SessionEngine configuration safely with deepcopy
    import copy
    original_configs = copy.deepcopy(SessionEngine.SESSION_CONFIGS)
    try:
        SessionEngine.SESSION_CONFIGS["asian"]["start"] = time(1, 0)
        SessionEngine.SESSION_CONFIGS["london"]["start"] = time(2, 0)
        SessionEngine.SESSION_CONFIGS["new_york"]["start"] = time(3, 0)

        # Re-compute 7H window
        w2_start, w2_end = SevenHourProfileEngine.get_window_for_timestamp(sample_dt, cfg)

        # 7H boundaries must remain strictly identical
        assert w1_start == w2_start
        assert w1_end == w2_end
    finally:
        SessionEngine.SESSION_CONFIGS = original_configs

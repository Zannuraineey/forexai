import pytest
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from sqlalchemy import select

from app.schemas.candle import CandleRead
from app.schemas.seven_hour_profile import (
    SevenHourProfileConfig,
    SevenHourProfileResult,
    ProfileClassification,
    ProfileDirection,
    ProfileStatus,
    DataQuality,
)
from app.schemas.market_state import (
    StructuredMarketState,
    SevenHourProfileContext,
    SessionContext,
    HistoricalProfileContext,
)
from app.schemas.ai_analysis import AIAnalysisRequest
from app.models.instrument import Instrument
from app.models.candle import Candle
from app.services.session.session_engine import SessionEngine
from app.services.profiling.seven_hour_profile_engine import SevenHourProfileEngine
from app.services.context.market_context_assembler import MarketContextAssembler
from app.services.ai.ai_engine import AIAnalysisEngine
from app.services.ai.deterministic_provider import DeterministicAIProvider


def make_candle(
    ts: datetime,
    o: float = 1.1000,
    h: float = 1.1050,
    l: float = 1.0950,
    c: float = 1.1020,
    tf: str = "1h",
    symbol: str = "EURUSD",
    inst_id: int = 1,
    id_: int = 1,
) -> CandleRead:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return CandleRead(
        id=id_,
        instrument_id=inst_id,
        timeframe=tf,
        timestamp_utc=ts,
        open=o,
        high=h,
        low=l,
        close=c,
        volume=100.0,
        provider="deriv",
        is_complete=True,
    )


# 1. 7H context is available independently
def test_1_seven_hour_context_available_independently():
    """Verify that 7H profile can be built and adapted without any session state."""
    cfg = SevenHourProfileConfig(anchor_timezone="UTC", anchor_start=time(0, 0))
    t_start = datetime(2026, 10, 5, 0, 0, tzinfo=timezone.utc)
    t_end = t_start + timedelta(hours=7)
    candles = [make_candle(t_start + timedelta(hours=i), c=1.1000 + i*0.001) for i in range(7)]

    p_res = SevenHourProfileEngine.build_synthetic_profile(
        symbol="EURUSD",
        window_start_utc=t_start,
        window_end_utc=t_end,
        candles_in_window=candles,
        config=cfg,
        current_time_utc=t_end,
    )
    p_ctx = MarketContextAssembler.build_seven_hour_context(p_res)

    assert p_ctx.status == ProfileStatus.COMPLETED
    assert p_ctx.direction == ProfileDirection.BULLISH
    assert p_ctx.range > 0
    assert p_ctx.data_quality == DataQuality.COMPLETE
    assert p_ctx.source_candle_count == 7


# 2. Session context is available independently
def test_2_session_context_available_independently():
    """Verify that Session context can be evaluated without any 7H profile."""
    t_utc = datetime(2026, 10, 5, 8, 30, tzinfo=timezone.utc) # London open
    sess_state = SessionEngine.evaluate_sessions(t_utc)
    s_ctx = MarketContextAssembler.build_session_context(sess_state, t_utc)

    assert "london" in s_ctx.active_sessions
    assert s_ctx.primary_session == "london"
    assert s_ctx.killzone.get("is_killzone") is True
    assert "London" in s_ctx.killzone.get("name", "")


# 3. Both can coexist in StructuredMarketState
def test_3_both_coexist_in_structured_market_state():
    """Verify that StructuredMarketState cleanly houses both 7H and session context without coupling."""
    t_now = datetime(2026, 10, 5, 8, 30, tzinfo=timezone.utc)
    curr_c = make_candle(t_now, c=1.1080)
    c_1h = [make_candle(datetime(2026, 10, 5, i, 0, tzinfo=timezone.utc), c=1.1000 + i*0.001) for i in range(9)]

    state = MarketContextAssembler.assemble(
        symbol="EURUSD",
        requested_timeframe="15m",
        current_candle=curr_c,
        candles_by_timeframe={"1h": c_1h, "15m": [curr_c]},
    )

    assert isinstance(state, StructuredMarketState)
    assert state.symbol == "EURUSD"
    assert state.timestamp_utc == t_now
    assert state.seven_hour_profile is not None
    assert state.seven_hour_profile.status in (ProfileStatus.COMPLETED, ProfileStatus.IN_PROGRESS)
    assert state.session is not None
    assert "london" in state.session.active_sessions
    assert state.profile_vs_session_interaction is not None
    assert state.profile_vs_session_interaction.active_session == "london"


# 4. Changing session configuration does not change 7H profile
def test_4_changing_session_config_does_not_affect_7h_profile():
    cfg = SevenHourProfileConfig(anchor_timezone="UTC", anchor_start=time(0, 0))
    t_start = datetime(2026, 10, 5, 0, 0, tzinfo=timezone.utc)
    candles = [make_candle(t_start + timedelta(hours=i), c=1.1010) for i in range(7)]

    # 7H profile before session mutation
    p_before = SevenHourProfileEngine.build_synthetic_profile(
        "EURUSD", t_start, t_start + timedelta(hours=7), candles, cfg, current_time_utc=t_start + timedelta(hours=7)
    )

    import copy
    orig_configs = copy.deepcopy(SessionEngine.SESSION_CONFIGS)
    try:
        SessionEngine.SESSION_CONFIGS["asian"]["start"] = time(3, 0)
        SessionEngine.SESSION_CONFIGS["london"]["start"] = time(11, 0)

        # 7H profile after session mutation
        p_after = SevenHourProfileEngine.build_synthetic_profile(
            "EURUSD", t_start, t_start + timedelta(hours=7), candles, cfg, current_time_utc=t_start + timedelta(hours=7)
        )

        assert p_before.profile_start == p_after.profile_start
        assert p_before.profile_end == p_after.profile_end
        assert p_before.classification == p_after.classification
        assert p_before.range == p_after.range
    finally:
        SessionEngine.SESSION_CONFIGS = orig_configs


# 5. Changing 7H anchor does not change SessionEngine
def test_5_changing_7h_anchor_does_not_affect_session_engine():
    t_sample = datetime(2026, 10, 5, 9, 0, tzinfo=timezone.utc)
    sess_before = SessionEngine.evaluate_sessions(t_sample)

    # Instantiate two completely different 7H anchor configs
    cfg1 = SevenHourProfileConfig(anchor_start=time(0, 0), anchor_timezone="UTC")
    cfg2 = SevenHourProfileConfig(anchor_start=time(17, 0), anchor_timezone="America/New_York")

    w1_s, w1_e = SevenHourProfileEngine.get_window_for_timestamp(t_sample, cfg1)
    w2_s, w2_e = SevenHourProfileEngine.get_window_for_timestamp(t_sample, cfg2)
    assert w1_s != w2_s  # 7H anchors differ

    # SessionEngine evaluation is completely unperturbed
    sess_after = SessionEngine.evaluate_sessions(t_sample)
    assert sess_before.active_sessions == sess_after.active_sessions
    assert sess_before.primary_session == sess_after.primary_session


# 6. Profile direction is not converted directly into a trade
def test_6_profile_direction_not_converted_directly_into_trade():
    """Verify that BULLISH or BEARISH profile direction produces NO trade proposal in assembler."""
    t_now = datetime(2026, 10, 5, 8, 0, tzinfo=timezone.utc)
    curr_c = make_candle(t_now, c=1.1100)

    # Bullish profile
    p_bull = SevenHourProfileResult(
        symbol="EURUSD",
        profile_start=t_now - timedelta(hours=7),
        profile_end=t_now,
        status=ProfileStatus.COMPLETED,
        open=1.1000,
        high=1.1120,
        low=1.0990,
        close=1.1100,
        direction=ProfileDirection.BULLISH,
        range=0.0130,
        body=0.0100,
        body_ratio=0.769,
        close_location=0.846,
        features=SevenHourProfileEngine.build_synthetic_profile(
            "EURUSD", t_now - timedelta(hours=7), t_now, [curr_c], SevenHourProfileConfig(), current_time_utc=t_now
        ).features,
        previous_profile=None,
        relationship=None,
        classification=ProfileClassification.BULLISH_EXPANSION,
        source_timeframe="1h",
        source_candle_count=7,
        expected_candle_count=7,
        data_quality=DataQuality.COMPLETE,
        config_id="UTC_0000_7H",
    )

    state = MarketContextAssembler.assemble(
        symbol="EURUSD",
        requested_timeframe="1h",
        current_candle=curr_c,
        candles_by_timeframe={"1h": [curr_c]},
        seven_hour_profile=p_bull,
    )

    # StructuredMarketState does NOT generate trade proposals or buy/sell orders
    assert state.seven_hour_profile.direction == ProfileDirection.BULLISH
    assert state.seven_hour_profile.classification == ProfileClassification.BULLISH_EXPANSION
    # Factual cross-layer interaction without trade directive
    assert state.profile_vs_session_interaction.profile_direction == ProfileDirection.BULLISH
    assert not hasattr(state, "action")
    assert not hasattr(state, "trade_setup")


# 7. Missing 7H data does not crash analysis
def test_7_missing_7h_data_does_not_crash_analysis():
    t_now = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)
    curr_c = make_candle(t_now)

    # No 7H profile passed and empty candles for 7H
    state = MarketContextAssembler.assemble(
        symbol="EURUSD",
        requested_timeframe="15m",
        current_candle=curr_c,
        candles_by_timeframe={}, # completely empty
        seven_hour_profile=None,
    )

    assert state.seven_hour_profile.data_quality == DataQuality.INSUFFICIENT
    assert state.seven_hour_profile.classification == ProfileClassification.INSUFFICIENT_DATA
    assert state.seven_hour_profile.direction == ProfileDirection.NEUTRAL


# 8. Missing session data does not crash profile calculation
def test_8_missing_session_data_does_not_crash():
    t_now = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)
    curr_c = make_candle(t_now)

    state = MarketContextAssembler.assemble(
        symbol="EURUSD",
        requested_timeframe="15m",
        current_candle=curr_c,
        candles_by_timeframe={"15m": [curr_c]},
        session_state=None, # explicitly None
    )

    assert state.session is not None
    assert isinstance(state.session.active_sessions, list)


# 9. No future 7H data leaks into current context
def test_9_no_future_7h_data_leaks_into_current_context():
    cfg = SevenHourProfileConfig()
    t_base = datetime(2026, 10, 5, 0, 0, tzinfo=timezone.utc)

    # 14 hours of candles: first 7 hours normal, next 7 hours spike to 1.3000
    c_hist = [make_candle(t_base + timedelta(hours=i), c=1.1000) for i in range(7)]
    c_future = [make_candle(t_base + timedelta(hours=7 + i), c=1.3000, h=1.3500) for i in range(7)]

    # Assemble at evaluation time t = 07:00 (end of Window 1)
    eval_c = c_hist[-1]
    # Pass only available candles up to current evaluation time
    state = MarketContextAssembler.assemble(
        symbol="EURUSD",
        requested_timeframe="1h",
        current_candle=eval_c,
        candles_by_timeframe={"1h": c_hist},
        seven_hour_config=cfg,
    )

    assert state.seven_hour_profile.range < 0.05
    assert state.current_price == 1.1000
    assert state.timestamp_utc <= t_base + timedelta(hours=7)


# 10. Timestamp alignment and historical profile context
def test_10_timestamp_alignment_and_historical_profile_context():
    t_now = datetime(2026, 10, 5, 14, 0, tzinfo=timezone.utc)
    curr_c = make_candle(t_now, c=1.1050)

    # When historical profile statistics are unavailable: return null / unavailable, NEVER invent probabilities
    hist_ctx = HistoricalProfileContext()
    assert hist_ctx.profile_sample_size is None
    assert hist_ctx.profile_win_rate is None
    assert hist_ctx.historical_mfe is None
    assert hist_ctx.historical_mae is None
    assert hist_ctx.historical_r_multiple_distribution is None

    state = MarketContextAssembler.assemble(
        symbol="EURUSD",
        requested_timeframe="1h",
        current_candle=curr_c,
        candles_by_timeframe={"1h": [curr_c]},
        historical_profile_context=hist_ctx,
    )

    assert state.timestamp_utc == t_now
    assert state.historical_profile_context.profile_win_rate is None


# 11. End-to-end integration with AIAnalysisEngine
@pytest.mark.asyncio
async def test_11_ai_analysis_engine_assembles_structured_market_state(db_session):
    inst_res = await db_session.execute(select(Instrument).where(Instrument.symbol == "EURUSD"))
    inst = inst_res.scalar_one_or_none()
    if not inst:
        inst = Instrument(symbol="EURUSD", base_asset="EUR", quote_asset="USD", pip_size=0.0001, is_active=True)
        db_session.add(inst)
        await db_session.commit()
        await db_session.refresh(inst)

    t_start = datetime(2026, 10, 5, 8, 0, tzinfo=timezone.utc)
    for i in range(10):
        c = Candle(
            instrument_id=inst.id,
            timeframe="15m",
            timestamp_utc=t_start + timedelta(minutes=15 * i),
            open=1.1000,
            high=1.1020,
            low=1.0980,
            close=1.1010,
            volume=50.0,
            provider="deriv",
            is_complete=True,
        )
        db_session.add(c)
    await db_session.commit()

    engine = AIAnalysisEngine(db_session)
    req = AIAnalysisRequest(
        symbol="EURUSD",
        timeframe="15m",
        custom_instructions="Only consider a setup after price sweeps the Asian high.",
    )

    record = await engine.execute_analysis(req)
    assert record.id is not None
    assert record.symbol == "EURUSD"

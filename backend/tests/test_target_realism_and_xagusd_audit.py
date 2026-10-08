import pytest
import math
from datetime import datetime, timezone, timedelta

from app.services.ai.deterministic_provider import DeterministicAIProvider
from app.services.features.target_realism import TargetRealismAnalyzer
from app.schemas.target_realism import TargetClassification, TargetRealismMetrics
from app.schemas.setup_snapshot import SetupContextSnapshot
from app.models.trade_outcome import TradeSetupOutcome
from app.services.tracking.outcome_tracker import TradeOutcomeTracker
from app.services.context.market_context_assembler import MarketContextAssembler


# ==============================================================================
# 1. XAGUSD 58.95 / 58.87 / 60.60 GEOMETRY
# ==============================================================================
def test_1_xagusd_reference_setup_geometry():
    """
    Test 1: Verify the reference XAGUSD setup geometry:
    BUY LIMIT @ 58.95, SL: 58.87, TP2: 60.60.
    Must satisfy SL < Entry < TP.
    """
    entry = 58.95
    sl = 58.87
    tp2 = 60.60

    res = DeterministicAIProvider.validate_trade_geometry(
        action="BUY LIMIT",
        entry_price=entry,
        stop_loss=sl,
        take_profit=tp2,
    )

    assert res["valid"] is True
    assert res["risk_distance"] == pytest.approx(0.08, abs=1e-5)
    assert res["reward_distance"] == pytest.approx(1.65, abs=1e-5)
    assert res["rr_ratio"] > 1.8


# ==============================================================================
# 2. CORRECT 20.625R CALCULATION
# ==============================================================================
def test_2_correct_20_625r_calculation():
    """
    Test 2: Verify exact calculation for:
    Entry = 58.95, SL = 58.87, TP = 60.60.
    Risk = 58.95 - 58.87 = 0.08
    Reward = 60.60 - 58.95 = 1.65
    R:R = 1.65 / 0.08 = 20.625R (reported as ~20.62R in UI).
    """
    entry = 58.95
    sl = 58.87
    tp = 60.60

    risk = entry - sl
    reward = tp - entry
    rr = reward / risk

    assert rr == pytest.approx(20.625, abs=1e-5)
    assert round(rr, 2) == 20.62

    res = DeterministicAIProvider.validate_trade_geometry(
        action="BUY LIMIT",
        entry_price=entry,
        stop_loss=sl,
        take_profit=tp,
    )
    # validate_trade_geometry outputs standard 2-decimal rounded R:R (20.62R matching reference setup)
    assert res["rr_ratio"] == 20.62


# ==============================================================================
# 3. EXTREME-TARGET CLASSIFICATION
# ==============================================================================
def test_3_extreme_target_classification():
    """
    Test 3: TargetRealismAnalyzer must classify the 20.625R target as EXTREME_TARGET.
    A setup requiring > 10R or > 4.0x ATR should not be labeled a NORMAL target.
    """
    analyzer = TargetRealismAnalyzer()

    # Normal target: 2.5R, 1.0 ATR
    normal_metrics = analyzer.analyze_target(
        symbol="XAGUSD",
        direction="BUY",
        entry_price=58.95,
        stop_loss=58.87,
        take_profit=59.15,
        atr=0.20,
    )
    assert normal_metrics.classification == TargetClassification.NORMAL_TARGET

    # Reference setup: 20.625R, reward = 1.65, ATR = 0.20 (8.25x ATR)
    extreme_metrics = analyzer.analyze_target(
        symbol="XAGUSD",
        direction="BUY",
        entry_price=58.95,
        stop_loss=58.87,
        take_profit=60.60,
        atr=0.20,
    )
    assert extreme_metrics.classification == TargetClassification.EXTREME_TARGET
    assert extreme_metrics.rr_ratio == 20.62
    assert extreme_metrics.target_distance_atr == pytest.approx(8.25, abs=1e-3)

    # Beyond available context: target exceeds session/daily extremes when provided
    beyond_metrics = analyzer.analyze_target(
        symbol="XAGUSD",
        direction="BUY",
        entry_price=58.95,
        stop_loss=58.87,
        take_profit=65.00,
        daily_high=60.00,
        atr=0.20,
    )
    assert beyond_metrics.classification == TargetClassification.TARGET_BEYOND_AVAILABLE_CONTEXT


# ==============================================================================
# 4. NO ABS() R:R WORKAROUND
# ==============================================================================
def test_4_no_abs_rr_workaround():
    """
    Test 4: Verify that an inverted setup (e.g. BUY with TP < Entry)
    fails geometry validation and NEVER returns positive R:R using abs().
    """
    # Inverted BUY: TP (58.00) < Entry (58.95)
    res_buy_inv = DeterministicAIProvider.validate_trade_geometry(
        action="BUY LIMIT",
        entry_price=58.95,
        stop_loss=58.87,
        take_profit=58.00,
    )
    assert res_buy_inv["valid"] is False
    assert res_buy_inv["rr_ratio"] == 0.0

    # Inverted SELL: TP (60.00) > Entry (58.95)
    res_sell_inv = DeterministicAIProvider.validate_trade_geometry(
        action="SELL LIMIT",
        entry_price=58.95,
        stop_loss=59.05,
        take_profit=60.00,
    )
    assert res_sell_inv["valid"] is False
    assert res_sell_inv["rr_ratio"] == 0.0


# ==============================================================================
# 5. FILL PRICE DIFFERENT FROM SIGNAL PRICE
# ==============================================================================
def test_5_fill_price_different_from_signal_price():
    """
    Test 5: The outcome tracking layer must record fill price vs signal price,
    quantifying execution slippage (e.g. Signal = 58.95, Actual Displayed/Fill = 58.98).
    """
    tracker = TradeOutcomeTracker()
    now = datetime.now(timezone.utc)

    outcome = tracker.initialize_outcome(
        setup_id="test_xagusd_001",
        symbol="XAGUSD",
        direction="BUY",
        signal_entry=58.95,
        stop_loss=58.87,
        take_profit=60.60,
        signal_timestamp=now,
    )

    # Initial state: no fill yet
    assert outcome.signal_entry == 58.95
    assert outcome.fill_price is None
    assert outcome.slippage == 0.0

    # Order executed with adverse slippage at 58.98
    filled = tracker.record_fill(
        outcome=outcome,
        fill_price=58.98,
        fill_timestamp=now + timedelta(seconds=45),
    )

    assert filled.fill_price == 58.98
    assert filled.slippage == pytest.approx(0.03, abs=1e-5)  # 58.98 - 58.95
    assert filled.outcome == "FILLED"


# ==============================================================================
# 6. 7H CONTEXT ATTACHED TO SETUP
# ==============================================================================
def test_6_seven_hour_context_attached():
    """
    Test 6: Candidate setups must contain 7H Profile conditioning variables
    in the structured snapshot without using 7H to directly trigger orders.
    """
    profile_data = {
        "seven_hour_profile": "BEARISH_EXPANSION",
        "seven_hour_direction": "BEARISH",
        "seven_hour_classification": "EXPANSION",
        "seven_hour_range": 0.45,
        "seven_hour_relationship": "OUTSIDE_BAR",
    }

    snapshot = SetupContextSnapshot(
        symbol="XAGUSD",
        timestamp=datetime.now(timezone.utc).isoformat(),
        profile=profile_data,
        session={},
        htf={},
        structure={},
        liquidity={},
        dxy={},
        news={},
        entry=58.95,
        stop_loss=58.87,
        tp1=59.07,
        tp2=60.60,
        risk_distance=0.08,
        rr_tp1=1.5,
        rr_tp2=20.625,
        target_quality="EXTREME_TARGET",
        data_quality="COMPLETE",
    )

    assert snapshot.profile["seven_hour_profile"] == "BEARISH_EXPANSION"
    assert snapshot.profile["seven_hour_direction"] == "BEARISH"
    assert snapshot.profile["seven_hour_range"] == 0.45


# ==============================================================================
# 7. SESSION CONTEXT ATTACHED TO SETUP
# ==============================================================================
def test_7_session_context_attached():
    """
    Test 7: SetupContextSnapshot must contain session variables
    (primary_session, active_sessions, killzone, session_high, session_low).
    """
    session_data = {
        "primary_session": "New York",
        "active_sessions": ["New York"],
        "killzone": "NY AM",
        "session_high": 59.20,
        "session_low": 58.80,
        "session_sweep": "ASIAN_LOW_SWEPT",
        "session_range": 0.40,
    }

    snapshot = SetupContextSnapshot(
        symbol="XAGUSD",
        timestamp=datetime.now(timezone.utc).isoformat(),
        profile={},
        session=session_data,
        htf={},
        structure={},
        liquidity={},
        dxy={},
        news={},
        entry=58.95,
        stop_loss=58.87,
        tp1=59.07,
        tp2=60.60,
        risk_distance=0.08,
        rr_tp1=1.5,
        rr_tp2=20.625,
        target_quality="EXTREME_TARGET",
        data_quality="COMPLETE",
    )

    assert snapshot.session["primary_session"] == "New York"
    assert snapshot.session["killzone"] == "NY AM"
    assert snapshot.session["session_sweep"] == "ASIAN_LOW_SWEPT"


# ==============================================================================
# 8. DXY CONTEXT ATTACHED WHEN RELEVANT
# ==============================================================================
def test_8_dxy_context_attached():
    """
    Test 8: DXY intermarket context must be attached for USD pairs/metals (XAGUSD).
    When DXY is BULLISH, for a BUY on XAGUSD, relationship must be CONTRADICTING.
    """
    assembler = MarketContextAssembler()

    dxy_context = assembler._build_dxy_context(
        symbol="XAGUSD",
        direction="BUY",
        dxy_data={"direction": "BULLISH", "trend_strength": 0.85, "change": 0.35},
    )

    assert dxy_context["dxy_direction"] == "BULLISH"
    assert dxy_context["dxy_relationship_to_symbol"] == "CONTRADICTING"

    # If symbol were EURUSD and direction is SELL, BULLISH DXY is SUPPORTIVE
    dxy_supportive = assembler._build_dxy_context(
        symbol="EURUSD",
        direction="SELL",
        dxy_data={"direction": "BULLISH", "trend_strength": 0.80, "change": 0.20},
    )
    assert dxy_supportive["dxy_relationship_to_symbol"] == "SUPPORTIVE"

    # Graceful fallback when unavailable
    dxy_none = assembler._build_dxy_context(
        symbol="XAGUSD",
        direction="BUY",
        dxy_data=None,
    )
    assert dxy_none["dxy_relationship_to_symbol"] == "UNAVAILABLE"


# ==============================================================================
# 9. NEWS CONTEXT ATTACHED
# ==============================================================================
def test_9_news_context_attached():
    """
    Test 9: News context attached with risk metrics, or explicit UNAVAILABLE state.
    """
    assembler = MarketContextAssembler()

    news_data = {
        "high_impact_news_nearby": True,
        "news_direction": "BEARISH_USD",
        "news_event": "US CPI MoM",
        "minutes_to_event": 12,
        "minutes_since_event": None,
        "usd_news_risk": "HIGH",
    }
    news_ctx = assembler._build_news_context("XAGUSD", news_data)
    assert news_ctx["high_impact_news_nearby"] is True
    assert news_ctx["news_event"] == "US CPI MoM"
    assert news_ctx["usd_news_risk"] == "HIGH"

    news_none = assembler._build_news_context("XAGUSD", None)
    assert news_none["high_impact_news_nearby"] is False
    assert news_none["usd_news_risk"] == "UNAVAILABLE"


# ==============================================================================
# 10. MISSING HISTORICAL DATA DOES NOT CREATE FAKE STATISTICS
# ==============================================================================
def test_10_missing_historical_data_does_not_create_fake_stats():
    """
    Test 10: Never manufacture probability metrics like "20R has 80% probability"
    without historical trade samples. When sample_size == 0, report INSUFFICIENT_DATA.
    """
    tracker = TradeOutcomeTracker()
    stats = tracker.get_historical_statistics(symbol="XAGUSD", setups_history=[])

    assert stats["sample_size"] == 0
    assert stats["statistics_status"] == "INSUFFICIENT_DATA"
    assert stats["win_rate"] is None
    assert stats["avg_r_multiple"] is None
    assert "reaches_20r" not in stats or stats["reaches_20r"] is None


# ==============================================================================
# 11. OUTCOME DATA RECORDS MFE / MAE CORRECTLY
# ==============================================================================
def test_11_outcome_data_records_mfe_mae_correctly():
    """
    Test 11: TradeOutcomeTracker must track:
    - Max Favorable Excursion (MFE)
    - Max Adverse Excursion (MAE)
    - Milestone timestamps (1R, 2R, 3R, 5R, etc.)
    - Hit SL / Hit TP outcome and final R-multiple.
    """
    tracker = TradeOutcomeTracker()
    now = datetime.now(timezone.utc)

    # Reconstruct the reference XAGUSD scenario:
    # BUY @ 58.95, SL: 58.87, TP: 60.60
    # Risk = 0.08
    outcome = tracker.initialize_outcome(
        setup_id="xagusd_forensic_01",
        symbol="XAGUSD",
        direction="BUY",
        signal_entry=58.95,
        stop_loss=58.87,
        take_profit=60.60,
        signal_timestamp=now,
    )
    outcome = tracker.record_fill(outcome, fill_price=58.95, fill_timestamp=now)

    # 1. Price ticks up slightly to 59.05 (Favorable excursion = 0.10, which is > 1R = 0.08)
    t1 = now + timedelta(minutes=5)
    outcome = tracker.update_price_tick(outcome, high=59.05, low=58.94, timestamp=t1)
    assert outcome.max_favorable_excursion == pytest.approx(0.10, abs=1e-5)
    assert outcome.max_adverse_excursion == pytest.approx(0.01, abs=1e-5)
    assert outcome.reached_1r is True
    assert outcome.time_to_1r_seconds == 300

    # 2. Price turns around and drops, breaking levels and hitting SL at 58.86
    t2 = now + timedelta(minutes=25)
    outcome = tracker.update_price_tick(outcome, high=59.00, low=58.86, timestamp=t2)
    assert outcome.max_adverse_excursion == pytest.approx(0.09, abs=1e-5)
    assert outcome.reached_sl is True
    assert outcome.outcome == "STOPPED_OUT"
    assert outcome.final_r_multiple == pytest.approx(-1.0, abs=1e-4)
    assert outcome.time_to_sl_seconds == 1500
    assert outcome.reached_20r is False

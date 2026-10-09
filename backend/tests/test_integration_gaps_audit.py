import pytest
from datetime import datetime, timezone, timedelta
from typing import List

from app.schemas.candle import CandleRead
from app.schemas.bias_validation import (
    FinalBiasState,
    BiasQuality,
    SevenHourRelationship,
    DXYRelationship,
    NewsRiskLevel,
)
from app.schemas.seven_hour_profile import ProfileStatus, ProfileDirection, ProfileClassification
from app.schemas.market_state import (
    StructuredMarketState,
    SevenHourProfileContext,
    SessionContext,
    TimeframeContext,
    TimeframeSummary,
    StructureContext,
    LiquidityContext,
    ProfileSessionInteraction,
)
from app.schemas.target_realism import TargetClassification
from app.services.bias.bias_validation_engine import BiasValidationEngine
from app.services.features.target_realism import TargetRealismAnalyzer
from app.services.tracking.outcome_tracker import TradeOutcomeTracker
from app.services.ai.deterministic_provider import DeterministicAIProvider


def _make_candle(ts: datetime, o: float, h: float, l: float, c: float) -> CandleRead:
    return CandleRead(
        id=1,
        instrument_id=1,
        timeframe="15m",
        timestamp_utc=ts,
        open=o,
        high=h,
        low=l,
        close=c,
        volume=100.0,
        provider="DERIV",
        is_complete=True,
    )


# =====================================================================
# 1. DXY and News Data Reaching Bias Validation
# =====================================================================
def test_1_dxy_and_news_data_reach_bias_validation():
    """Verify that real DXY and News dictionaries inside structured_state reach validation."""
    ts = datetime(2026, 10, 8, 12, 0, tzinfo=timezone.utc)
    
    dxy_dict = {
        "direction": "BEARISH",
        "trend_strength": "CONFIRMING_BEARISH",
        "change": -0.45,
        "dxy_relationship_to_symbol": "SUPPORTIVE",
    }
    news_dict = {
        "risk_level": "LOW_RISK",
        "high_impact_news_nearby": False,
        "news_event": None,
        "usd_news_risk": "LOW",
        "status": "ACTIVE_NO_NEARBY_EVENT",
    }

    state = StructuredMarketState(
        symbol="EURUSD",
        timestamp_utc=ts,
        current_price=1.1000,
        seven_hour_profile=SevenHourProfileContext(
            status=ProfileStatus.COMPLETED,
            direction=ProfileDirection.BULLISH,
            classification=ProfileClassification.BULLISH_EXPANSION,
        ),
        session=SessionContext(primary_session="london"),
        timeframe_context=TimeframeContext(
            tf_4h=TimeframeSummary(timeframe="4h", trend="BULLISH"),
            tf_1h=TimeframeSummary(timeframe="1h", trend="BULLISH"),
            tf_15m=TimeframeSummary(timeframe="15m", trend="BULLISH"),
            requested_timeframe="15m",
        ),
        structure=StructureContext(trend="BULLISH"),
        liquidity=LiquidityContext(),
        profile_vs_session_interaction=ProfileSessionInteraction(),
        dxy=dxy_dict,
        news=news_dict,
    )

    result = BiasValidationEngine.validate_bias(symbol="EURUSD", timestamp=ts, structured_state=state)

    # For EURUSD (USD quote): DXY Bearish => USD weaker => EURUSD rises => SUPPORTIVE of BULLISH bias
    assert result.dxy_context["relationship"] == DXYRelationship.SUPPORTIVE
    assert result.dxy_context["dxy_direction"] == "BEARISH"
    assert result.news_context["risk_level"] == NewsRiskLevel.LOW_RISK
    assert result.final_bias == FinalBiasState.BULLISH


# =====================================================================
# 2. Distinguishing Missing vs Neutral DXY and News
# =====================================================================
def test_2_missing_vs_neutral_dxy_and_news():
    """Verify system distinguishes UNAVAILABLE from NEUTRAL/LOW without fabricating values."""
    # A. Missing DXY and News
    dxy_missing = BiasValidationEngine.evaluate_dxy_relationship(
        symbol="EURUSD",
        proposed_bias="BULLISH",
        dxy_data=None,
    )
    assert dxy_missing["relationship"] == DXYRelationship.UNAVAILABLE
    assert dxy_missing["dxy_direction"] == "UNAVAILABLE"

    news_missing = BiasValidationEngine.evaluate_news_context(
        symbol="EURUSD",
        news_data={"status": "UNAVAILABLE", "usd_news_risk": "UNAVAILABLE"},
    )
    assert news_missing["risk_level"] == NewsRiskLevel.UNAVAILABLE
    assert news_missing["usd_news_risk"] == "UNAVAILABLE"

    # B. Neutral DXY and Low Risk News
    dxy_neutral = BiasValidationEngine.evaluate_dxy_relationship(
        symbol="EURUSD",
        proposed_bias="BULLISH",
        dxy_data={"direction": "NEUTRAL", "trend_strength": "NEUTRAL"},
    )
    assert dxy_neutral["relationship"] == DXYRelationship.NEUTRAL

    news_neutral = BiasValidationEngine.evaluate_news_context(
        symbol="EURUSD",
        news_data={"high_impact_news_nearby": False, "usd_news_risk": "LOW"},
    )
    assert news_neutral["risk_level"] == NewsRiskLevel.LOW_RISK


# =====================================================================
# 3. DXY or News Cannot Independently Generate a Trade
# =====================================================================
def test_3_dxy_or_news_cannot_generate_bias_when_structure_is_neutral():
    """Verify DXY supportive flow alone does NOT turn NEUTRAL market structure into BULLISH."""
    ts = datetime(2026, 10, 8, 12, 0, tzinfo=timezone.utc)
    state = StructuredMarketState(
        symbol="EURUSD",
        timestamp_utc=ts,
        current_price=1.1000,
        seven_hour_profile=SevenHourProfileContext(
            status=ProfileStatus.COMPLETED,
            direction=ProfileDirection.NEUTRAL,
        ),
        session=SessionContext(primary_session="london"),
        timeframe_context=TimeframeContext(
            tf_4h=TimeframeSummary(timeframe="4h", trend="UNDEFINED"),
            tf_1h=TimeframeSummary(timeframe="1h", trend="CONSOLIDATION"),
            requested_timeframe="15m",
        ),
        structure=StructureContext(trend="UNDEFINED"),
        liquidity=LiquidityContext(),
        profile_vs_session_interaction=ProfileSessionInteraction(),
        dxy={"direction": "BEARISH", "trend_strength": "STRONG"},
        news={"high_impact_news_nearby": False, "usd_news_risk": "LOW"},
    )

    result = BiasValidationEngine.validate_bias(symbol="EURUSD", timestamp=ts, structured_state=state)
    assert result.final_bias == FinalBiasState.NEUTRAL
    assert "Session or liquidity events cannot independently generate directional bias" in result.explanation


# =====================================================================
# 4. Outcome Worker Idempotency
# =====================================================================
def test_4_outcome_lifecycle_idempotency():
    """Repeatedly evaluating lifecycle over the same candles produces identical outcomes."""
    sig_ts = datetime(2026, 10, 8, 10, 0, tzinfo=timezone.utc)
    candles = [
        _make_candle(sig_ts + timedelta(minutes=15), 1.1020, 1.1030, 1.0990, 1.1010), # fills at 1.1000
        _make_candle(sig_ts + timedelta(minutes=30), 1.1010, 1.1080, 1.1005, 1.1070), # hits 1R, 2R
        _make_candle(sig_ts + timedelta(minutes=45), 1.1070, 1.1150, 1.1060, 1.1140), # hits TP at 1.1120
    ]

    res1 = TradeOutcomeTracker.evaluate_candles_lifecycle(
        setup_id="setup_eur_1",
        symbol="EURUSD",
        action="BUY",
        entry=1.1000,
        stop_loss=1.0950,
        take_profit=1.1120,
        signal_timestamp_utc=sig_ts,
        subsequent_candles=candles,
    )

    res2 = TradeOutcomeTracker.evaluate_candles_lifecycle(
        setup_id="setup_eur_1",
        symbol="EURUSD",
        action="BUY",
        entry=1.1000,
        stop_loss=1.0950,
        take_profit=1.1120,
        signal_timestamp_utc=sig_ts,
        subsequent_candles=candles,
    )

    assert res1 == res2
    assert res1["outcome"] == "TP_HIT"
    assert res1["reached_1r"] is True
    assert res1["reached_2r"] is True
    assert res1["fill_price"] is None  # Simulated touch, broker fill price unknown


# =====================================================================
# 5. Entry Not Reached vs Entry Filled
# =====================================================================
def test_5_entry_not_reached_vs_entry_filled():
    """Limit entry not reached stays PENDING; entry reached tracks active lifecycle."""
    sig_ts = datetime(2026, 10, 8, 10, 0, tzinfo=timezone.utc)
    
    # Price never dips to 1.1000
    candles_unreached = [
        _make_candle(sig_ts + timedelta(minutes=15), 1.1050, 1.1070, 1.1020, 1.1060),
        _make_candle(sig_ts + timedelta(minutes=30), 1.1060, 1.1090, 1.1040, 1.1080),
    ]

    res_unreached = TradeOutcomeTracker.evaluate_candles_lifecycle(
        setup_id="setup_pending",
        symbol="EURUSD",
        action="BUY",
        entry=1.1000,
        stop_loss=1.0950,
        take_profit=1.1100,
        signal_timestamp_utc=sig_ts,
        subsequent_candles=candles_unreached,
    )
    assert res_unreached["outcome"] == "PENDING"
    assert res_unreached["entry_timestamp_utc"] is None
    assert res_unreached["reached_1r"] is False

    # Price dips to 1.0995 (reaches limit) with confirmed broker fill at 1.1002
    candles_reached = [
        _make_candle(sig_ts + timedelta(minutes=15), 1.1020, 1.1030, 1.0995, 1.1010),
    ]
    res_reached = TradeOutcomeTracker.evaluate_candles_lifecycle(
        setup_id="setup_filled",
        symbol="EURUSD",
        action="BUY",
        entry=1.1000,
        stop_loss=1.0950,
        take_profit=1.1100,
        signal_timestamp_utc=sig_ts,
        subsequent_candles=candles_reached,
        fill_price=1.1002,
    )
    assert res_reached["outcome"] == "ACTIVE"
    assert res_reached["fill_price"] == 1.1002
    assert res_reached["slippage"] == 0.0002


# =====================================================================
# 6. Ambiguous TP and SL Hits in One OHLC Candle
# =====================================================================
def test_6_ambiguous_tp_and_sl_hits_in_one_candle():
    """When both TP and SL are breached in the same bar, records AMBIGUOUS_INTRABAR."""
    sig_ts = datetime(2026, 10, 8, 10, 0, tzinfo=timezone.utc)
    
    # Long: Entry 1.1000, SL 1.0950, TP 1.1100.
    # Giant spike bar: Low 1.0920 (< SL) and High 1.1150 (> TP).
    candles = [
        _make_candle(sig_ts + timedelta(minutes=15), 1.1000, 1.1150, 1.0920, 1.1020),
    ]

    res = TradeOutcomeTracker.evaluate_candles_lifecycle(
        setup_id="setup_ambiguous",
        symbol="EURUSD",
        action="BUY",
        entry=1.1000,
        stop_loss=1.0950,
        take_profit=1.1100,
        signal_timestamp_utc=sig_ts,
        subsequent_candles=candles,
    )
    assert res["outcome"] == "AMBIGUOUS_INTRABAR"
    assert res["realized_r_multiple"] == 0.0


# =====================================================================
# 7. Target Classification vs Statistical Probability
# =====================================================================
def test_7_target_classification_vs_statistical_probability():
    """Extreme R:R target is classified factually without inventing win probabilities."""
    res = TargetRealismAnalyzer.evaluate_target(
        action="BUY",
        entry_price=1.1000,
        stop_loss=1.0990,  # 10 pips risk
        take_profit=1.1250, # 250 pips reward = 25.0R
        atr=0.0050,
        historical_outcomes=None,  # No historical dataset available
    )

    assert res.rr_ratio == 25.0
    assert res.classification == TargetClassification.EXTREME_TARGET
    assert res.policy_applied == "POLICY_ALLOWED_EXTREME_TARGET_WITH_TAGGING"
    # Never invents probability percentages
    assert res.statistical_support_status == "INSUFFICIENT_DATA"
    assert res.historical_hit_rate is None


# =====================================================================
# 8. 7H Completed vs In-Progress Boundaries
# =====================================================================
def test_8_7h_completed_vs_in_progress_boundaries():
    """In-progress 7H profiles are NOT treated as confirmed directional bias."""
    ts = datetime(2026, 10, 8, 12, 0, tzinfo=timezone.utc)

    # In-progress 7H profile
    state_in_progress = StructuredMarketState(
        symbol="EURUSD",
        timestamp_utc=ts,
        current_price=1.1000,
        seven_hour_profile=SevenHourProfileContext(
            status=ProfileStatus.IN_PROGRESS,
            direction=ProfileDirection.BULLISH,
            classification=ProfileClassification.BULLISH_EXPANSION,
        ),
        session=SessionContext(primary_session="london"),
        timeframe_context=TimeframeContext(
            tf_4h=TimeframeSummary(timeframe="4h", trend="BULLISH"),
            tf_1h=TimeframeSummary(timeframe="1h", trend="BULLISH"),
            requested_timeframe="15m",
        ),
        structure=StructureContext(trend="BULLISH"),
        liquidity=LiquidityContext(),
        profile_vs_session_interaction=ProfileSessionInteraction(),
    )

    res_in_progress = BiasValidationEngine.validate_bias(
        symbol="EURUSD", timestamp=ts, structured_state=state_in_progress
    )
    # 7H in progress is flagged as IN_PROGRESS, not confirmed SUPPORT
    assert res_in_progress.seven_hour_bias["role_to_htf"] == SevenHourRelationship.IN_PROGRESS

    # Completed 7H profile
    state_completed = StructuredMarketState(
        symbol="EURUSD",
        timestamp_utc=ts,
        current_price=1.1000,
        seven_hour_profile=SevenHourProfileContext(
            status=ProfileStatus.COMPLETED,
            direction=ProfileDirection.BULLISH,
            classification=ProfileClassification.BULLISH_EXPANSION,
        ),
        session=SessionContext(primary_session="london"),
        timeframe_context=TimeframeContext(
            tf_4h=TimeframeSummary(timeframe="4h", trend="BULLISH"),
            tf_1h=TimeframeSummary(timeframe="1h", trend="BULLISH"),
            requested_timeframe="15m",
        ),
        structure=StructureContext(trend="BULLISH"),
        liquidity=LiquidityContext(),
        profile_vs_session_interaction=ProfileSessionInteraction(),
    )

    res_completed = BiasValidationEngine.validate_bias(
        symbol="EURUSD", timestamp=ts, structured_state=state_completed
    )
    assert res_completed.seven_hour_bias["role_to_htf"] == SevenHourRelationship.SUPPORT


# =====================================================================
# 9. Existing Directional Trade Geometry Regressions
# =====================================================================
def test_9_directional_trade_geometry_regressions():
    """Verify geometry safety rules reject invalid or inverted orders."""
    provider = DeterministicAIProvider()

    # Valid BUY
    valid_buy = provider.validate_trade_geometry("BUY", 1.1000, 1.0950, 1.1100)
    assert valid_buy["valid"] is True
    assert valid_buy["rr_ratio"] == 2.0

    # Invalid BUY: SL above entry
    invalid_buy_sl = provider.validate_trade_geometry("BUY", 1.1000, 1.1050, 1.1100)
    assert invalid_buy_sl["valid"] is False

    # Invalid BUY: TP below entry
    invalid_buy_tp = provider.validate_trade_geometry("BUY", 1.1000, 1.0950, 1.0900)
    assert invalid_buy_tp["valid"] is False

    # Valid SELL
    valid_sell = provider.validate_trade_geometry("SELL", 1.1000, 1.1050, 1.0900)
    assert valid_sell["valid"] is True
    assert valid_sell["rr_ratio"] == 2.0

    # Invalid SELL: SL below entry
    invalid_sell_sl = provider.validate_trade_geometry("SELL", 1.1000, 1.0950, 1.0900)
    assert invalid_sell_sl["valid"] is False

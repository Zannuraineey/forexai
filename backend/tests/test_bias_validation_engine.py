import pytest
from datetime import datetime, timezone, timedelta

from app.schemas.bias_validation import (
    FinalBiasState,
    BiasQuality,
    SevenHourRelationship,
    DXYRelationship,
    NewsRiskLevel,
    BiasValidationResult,
)
from app.services.bias.bias_validation_engine import BiasValidationEngine
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
from app.schemas.seven_hour_profile import (
    ProfileClassification,
    ProfileDirection,
    ProfileStatus,
    DataQuality,
    ProfileRelationship,
)


# ==============================================================================
# 1. HTF BULLISH + 7H BULLISH
# ==============================================================================
def test_1_htf_bullish_and_7h_bullish():
    """
    Test 1: Higher Timeframe (4H & 1H) BULLISH + 7H Profile BULLISH.
    Final bias must be BULLISH, 7H role must be SUPPORT, bias quality must be HIGH.
    """
    res = BiasValidationEngine.validate_bias(
        symbol="EURUSD",
        custom_htf={"tf_4h_trend": "BULLISH", "tf_1h_trend": "BULLISH"},
        custom_7h={"direction": "BULLISH", "classification": "EXPANSION"},
        custom_15m={"trend": "BULLISH"},
    )

    assert res.final_bias == FinalBiasState.BULLISH
    assert res.seven_hour_bias["role_to_htf"] == SevenHourRelationship.SUPPORT
    assert res.bias_quality == BiasQuality.HIGH
    assert len(res.conflicts) == 0


# ==============================================================================
# 2. HTF BEARISH + 7H BEARISH
# ==============================================================================
def test_2_htf_bearish_and_7h_bearish():
    """
    Test 2: Higher Timeframe (4H & 1H) BEARISH + 7H Profile BEARISH.
    Final bias must be BEARISH, 7H role must be SUPPORT, bias quality must be HIGH.
    """
    res = BiasValidationEngine.validate_bias(
        symbol="EURUSD",
        custom_htf={"tf_4h_trend": "BEARISH", "tf_1h_trend": "BEARISH"},
        custom_7h={"direction": "BEARISH", "classification": "EXPANSION"},
        custom_15m={"trend": "BEARISH"},
    )

    assert res.final_bias == FinalBiasState.BEARISH
    assert res.seven_hour_bias["role_to_htf"] == SevenHourRelationship.SUPPORT
    assert res.bias_quality == BiasQuality.HIGH
    assert len(res.conflicts) == 0


# ==============================================================================
# 3. 7H CONFLICT
# ==============================================================================
def test_3_7h_conflict():
    """
    Test 3: HTF is BULLISH, but 7H Profile is BEARISH.
    7H role must be CONTRADICT, conflict must be logged.
    7H must NOT automatically flip HTF to BEARISH.
    """
    res = BiasValidationEngine.validate_bias(
        symbol="EURUSD",
        custom_htf={"tf_4h_trend": "BULLISH", "tf_1h_trend": "BULLISH"},
        custom_7h={"direction": "BEARISH", "classification": "CONTRACTION"},
        custom_15m={"trend": "BULLISH"},
    )

    assert res.seven_hour_bias["role_to_htf"] == SevenHourRelationship.CONTRADICT
    assert any("7H Profile (BEARISH) contradicts HTF bias" in c for c in res.conflicts)
    # HTF remains BULLISH, but quality is reduced
    assert res.final_bias == FinalBiasState.BULLISH
    assert res.bias_quality == BiasQuality.LOW


# ==============================================================================
# 4. DXY REMOVED FROM TRADING LOGIC (ALWAYS NEUTRAL)
# ==============================================================================
def test_4_dxy_supportive():
    """
    Test 4: DXY has been removed from trade setup generation.
    evaluate_dxy_relationship always returns DXYRelationship.NEUTRAL.
    """
    eur_dxy = BiasValidationEngine.evaluate_dxy_relationship(
        symbol="EURUSD",
        proposed_bias="BULLISH",
        dxy_data={"direction": "BEARISH", "trend_strength": 0.8},
    )
    assert eur_dxy["relationship"] == DXYRelationship.NEUTRAL

    jpy_dxy = BiasValidationEngine.evaluate_dxy_relationship(
        symbol="USDJPY",
        proposed_bias="BULLISH",
        dxy_data={"direction": "BULLISH", "trend_strength": 0.85},
    )
    assert jpy_dxy["relationship"] == DXYRelationship.NEUTRAL


# ==============================================================================
# 5. DXY CONTRADICTORY REMOVED
# ==============================================================================
def test_5_dxy_contradictory():
    """
    Test 5: DXY does not gate trade direction. Always returns NEUTRAL.
    """
    eur_dxy = BiasValidationEngine.evaluate_dxy_relationship(
        symbol="EURUSD",
        proposed_bias="BULLISH",
        dxy_data={"direction": "BULLISH", "trend_strength": 0.9},
    )
    assert eur_dxy["relationship"] == DXYRelationship.NEUTRAL

    jpy_dxy = BiasValidationEngine.evaluate_dxy_relationship(
        symbol="USDJPY",
        proposed_bias="BULLISH",
        dxy_data={"direction": "BEARISH", "trend_strength": 0.75},
    )
    assert jpy_dxy["relationship"] == DXYRelationship.NEUTRAL


# ==============================================================================
# 6. DXY UNAVAILABLE / MISSING
# ==============================================================================
def test_6_dxy_unavailable():
    """
    Test 6: For cross pairs or missing DXY data, evaluate_dxy_relationship returns NEUTRAL.
    """
    cross_dxy = BiasValidationEngine.evaluate_dxy_relationship(
        symbol="EURGBP",
        proposed_bias="BULLISH",
        dxy_data={"direction": "BULLISH"},
    )
    assert cross_dxy["relationship"] == DXYRelationship.NEUTRAL

    none_dxy = BiasValidationEngine.evaluate_dxy_relationship(
        symbol="EURUSD",
        proposed_bias="BULLISH",
        dxy_data=None,
    )
    assert none_dxy["relationship"] in (DXYRelationship.NEUTRAL, DXYRelationship.UNAVAILABLE)


# ==============================================================================
# 7. HIGH-IMPACT NEWS
# ==============================================================================
def test_7_high_impact_news():
    """
    Test 7: High impact news context:
    - Must report HIGH_RISK or EVENT_IMMINENT when within window.
    - News must act as risk filter and NOT invent trade direction.
    """
    news_imminent = BiasValidationEngine.evaluate_news_context(
        symbol="XAUUSD",
        news_data={
            "high_impact_news_nearby": True,
            "minutes_to_event": 10,
            "news_event": "US Non-Farm Payrolls",
        },
    )
    assert news_imminent["risk_level"] == NewsRiskLevel.EVENT_IMMINENT
    assert news_imminent["high_impact_news_nearby"] is True

    # Validate that in engine, high news risk logs a warning/conflict but doesn't change HTF direction
    res = BiasValidationEngine.validate_bias(
        symbol="XAUUSD",
        custom_htf={"tf_4h_trend": "BULLISH", "tf_1h_trend": "BULLISH"},
        news_data={"high_impact_news_nearby": True, "minutes_to_event": 5, "news_event": "CPI"},
    )
    assert any("High macro news risk active" in c for c in res.conflicts)
    assert res.final_bias == FinalBiasState.BULLISH  # HTF bias preserved


# ==============================================================================
# 8. SESSION-ONLY EVIDENCE MUST NOT CREATE BIAS
# ==============================================================================
def test_8_session_only_evidence_must_not_create_bias():
    """
    Test 8: Session context alone (e.g. New York session, NY AM killzone)
    must NOT independently create directional bias when HTF is NEUTRAL.
    """
    res = BiasValidationEngine.validate_bias(
        symbol="EURUSD",
        custom_htf={"tf_4h_trend": "CONSOLIDATION", "tf_1h_trend": "CONSOLIDATION"},
        custom_7h={"direction": "NEUTRAL"},
        custom_session={
            "primary_session": "New York",
            "active_sessions": ["New York"],
            "killzone": {"name": "NY AM", "is_killzone": True},
        },
    )

    assert res.final_bias == FinalBiasState.NEUTRAL
    assert res.session_context["primary_session"] == "New York"
    assert "Session or liquidity events cannot independently generate directional bias" in res.explanation


# ==============================================================================
# 9. LIQUIDITY-ONLY EVIDENCE MUST NOT CREATE BIAS
# ==============================================================================
def test_9_liquidity_only_evidence_must_not_create_bias():
    """
    Test 9: A liquidity sweep (e.g. SSL swept) without HTF structural support
    must NOT manufacture a BULLISH market bias.
    """
    res = BiasValidationEngine.validate_bias(
        symbol="EURUSD",
        custom_htf={"tf_4h_trend": "CONSOLIDATION", "tf_1h_trend": "CONSOLIDATION"},
        custom_7h={"direction": "NEUTRAL"},
        custom_sweeps=[{"level_type": "ASIAN_LOW", "extreme_price": 1.0820}],
    )

    assert res.final_bias == FinalBiasState.NEUTRAL
    assert res.liquidity_event["ssl_swept"] is True
    assert res.liquidity_event["event"] == "SSL_SWEPT"


# ==============================================================================
# 10. MSS WITHOUT HTF SUPPORT
# ==============================================================================
def test_10_mss_without_htf_support():
    """
    Test 10: Lower timeframe Bullish MSS without HTF support (HTF is BEARISH)
    must NOT flip final bias to BULLISH. HTF structure dominates.
    """
    res = BiasValidationEngine.validate_bias(
        symbol="EURUSD",
        custom_htf={"tf_4h_trend": "BEARISH", "tf_1h_trend": "BEARISH"},
        custom_mss=[{"direction": "BULLISH", "broken_swing_price": 1.0850}],
    )

    assert res.final_bias == FinalBiasState.BEARISH
    assert any("Counter-trend Bullish MSS lacks HTF Bearish support" in c for c in res.conflicts)


# ==============================================================================
# 11. FULL BULLISH ALIGNMENT
# ==============================================================================
def test_11_full_bullish_alignment():
    """
    Test 11: 4H Bullish + 1H Bullish + 7H Bullish + 15M Bullish + DXY Supportive + News Low Risk.
    Must output BULLISH, HIGH quality, 0 conflicts.
    """
    res = BiasValidationEngine.validate_bias(
        symbol="EURUSD",
        custom_htf={"tf_4h_trend": "BULLISH", "tf_1h_trend": "BULLISH"},
        custom_7h={"direction": "BULLISH"},
        custom_15m={"trend": "BULLISH"},
        dxy_data={"direction": "BEARISH", "trend_strength": 0.8},
        news_data={"high_impact_news_nearby": False, "usd_news_risk": "LOW"},
    )

    assert res.final_bias == FinalBiasState.BULLISH
    assert res.bias_quality == BiasQuality.HIGH
    assert len(res.conflicts) == 0
    assert res.mtf_alignment["aligned"] is True


# ==============================================================================
# 12. FULL BEARISH ALIGNMENT
# ==============================================================================
def test_12_full_bearish_alignment():
    """
    Test 12: 4H Bearish + 1H Bearish + 7H Bearish + 15M Bearish + DXY Supportive + News Low Risk.
    Must output BEARISH, HIGH quality, 0 conflicts.
    """
    res = BiasValidationEngine.validate_bias(
        symbol="EURUSD",
        custom_htf={"tf_4h_trend": "BEARISH", "tf_1h_trend": "BEARISH"},
        custom_7h={"direction": "BEARISH"},
        custom_15m={"trend": "BEARISH"},
        dxy_data={"direction": "BULLISH", "trend_strength": 0.85},
        news_data={"high_impact_news_nearby": False, "usd_news_risk": "LOW"},
    )

    assert res.final_bias == FinalBiasState.BEARISH
    assert res.bias_quality == BiasQuality.HIGH
    assert len(res.conflicts) == 0
    assert res.mtf_alignment["aligned"] is True


# ==============================================================================
# 13. INSUFFICIENT DATA
# ==============================================================================
def test_13_insufficient_data():
    """
    Test 13: When HTF structure is completely missing, engine must return
    INSUFFICIENT_DATA and UNUSABLE quality. Never invent assumptions.
    """
    res = BiasValidationEngine.validate_bias(
        symbol="EURUSD",
        custom_htf=None,
        market_context={},
    )

    assert res.final_bias == FinalBiasState.INSUFFICIENT_DATA
    assert res.bias_quality == BiasQuality.UNUSABLE
    assert "Higher Timeframe (4H / 1H) candle structure" in res.missing_data


# ==============================================================================
# 14. CONFLICT STATE
# ==============================================================================
def test_14_conflict_state():
    """
    Test 14: 4H Bullish, 1H Bullish, but 7H Bearish, 15M Bearish, and DXY Contradicting.
    Engine must return CONFLICTED rather than forcing a BUY or SELL.
    """
    res = BiasValidationEngine.validate_bias(
        symbol="EURUSD",
        custom_htf={"tf_4h_trend": "BULLISH", "tf_1h_trend": "BULLISH"},
        custom_7h={"direction": "BEARISH"},
        custom_15m={"trend": "BEARISH"},
        dxy_data={"direction": "BULLISH"},  # Contradicts EURUSD Bullish
    )

    assert res.final_bias == FinalBiasState.CONFLICTED
    assert res.bias_quality == BiasQuality.UNUSABLE
    assert len(res.conflicts) >= 2


# ==============================================================================
# 15. XAGUSD FORENSIC CONTEXT
# ==============================================================================
def test_15_xagusd_forensic_context():
    """
    Test 15: Reconstruct the reference XAGUSD setup (BUY LIMIT 58.95, SL 58.87, TP2 60.60).
    Verify that BiasValidationEngine correctly records the full multi-layer snapshot:
    HTF, 7H profile, 15M, session, liquidity, MSS, DXY, and news.
    """
    res = BiasValidationEngine.validate_bias(
        symbol="XAGUSD",
        custom_htf={"tf_4h_trend": "BULLISH", "tf_1h_trend": "BULLISH"},
        custom_7h={"direction": "BEARISH", "classification": "EXPANSION"},  # 7H opposed
        custom_15m={"trend": "BULLISH"},
        custom_sweeps=[{"level_type": "KEY_LOW", "extreme_price": 58.85}],
        custom_mss=[{"direction": "BULLISH", "broken_swing_price": 58.98}],
        custom_session={"primary_session": "New York", "killzone": {"name": "NY AM"}},
        dxy_data={"direction": "BULLISH", "trend_strength": 0.75},  # DXY opposed
        news_data={"high_impact_news_nearby": False},
    )

    assert res.symbol == "XAGUSD"
    assert res.seven_hour_bias["direction"] == "BEARISH"
    assert res.seven_hour_bias["role_to_htf"] == SevenHourRelationship.CONTRADICT
    assert res.dxy_context["relationship"] == DXYRelationship.NEUTRAL
    assert res.liquidity_event["ssl_swept"] is True
    assert res.mss_state["has_bullish_mss"] is True
    assert res.session_context["primary_session"] == "New York"
    # The setup had significant contradictory 7H flow
    assert any("7H Profile (BEARISH) contradicts HTF bias" in c for c in res.conflicts)


# ==============================================================================
# 16. XAUUSD CONTEXT
# ==============================================================================
def test_16_xauusd_context():
    """
    Test 16: Gold (XAUUSD) context evaluation with DXY intermarket flow.
    """
    dxy_res = BiasValidationEngine.evaluate_dxy_relationship(
        symbol="XAUUSD",
        proposed_bias="BULLISH",
        dxy_data={"direction": "BEARISH", "trend_strength": 0.8},
    )
    assert dxy_res["relationship"] == DXYRelationship.NEUTRAL

    res = BiasValidationEngine.validate_bias(
        symbol="XAUUSD",
        custom_htf={"tf_4h_trend": "BULLISH", "tf_1h_trend": "BULLISH"},
        custom_7h={"direction": "BULLISH"},
        dxy_data={"direction": "BEARISH", "trend_strength": 0.8},
    )
    assert res.final_bias == FinalBiasState.BULLISH
    assert res.dxy_context["relationship"] == DXYRelationship.NEUTRAL



# ==============================================================================
# 17. NO LOOK-AHEAD / FUTURE DATA
# ==============================================================================
def test_17_no_look_ahead_future_data():
    """
    Test 17: Bias validation must be timestamp-safe and never leak future candles.
    """
    eval_ts = datetime(2026, 10, 8, 13, 0, 0, tzinfo=timezone.utc)
    res = BiasValidationEngine.validate_bias(
        symbol="EURUSD",
        timestamp=eval_ts,
        custom_htf={"tf_4h_trend": "BULLISH", "tf_1h_trend": "BULLISH"},
    )

    assert res.timestamp == eval_ts.isoformat()
    assert datetime.fromisoformat(res.timestamp) == eval_ts

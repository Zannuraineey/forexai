import pytest
import math
from datetime import datetime, timezone, timedelta
from app.services.ai.deterministic_provider import DeterministicAIProvider
from app.models.analysis import AnalysisStateEnum

def test_1_valid_short_geometry():
    """Test 1: Valid SHORT (TP < Entry < SL)."""
    res = DeterministicAIProvider.validate_trade_geometry(
        action="SELL LIMIT",
        entry_price=4100.0,
        stop_loss=4105.0,
        take_profit=4090.0,
    )
    assert res["valid"] is True
    assert res["risk_distance"] == 5.0
    assert res["reward_distance"] == 10.0
    assert res["rr_ratio"] == 2.0


def test_2_valid_long_geometry():
    """Test 2: Valid LONG (SL < Entry < TP)."""
    res = DeterministicAIProvider.validate_trade_geometry(
        action="BUY LIMIT",
        entry_price=4100.0,
        stop_loss=4095.0,
        take_profit=4110.0,
    )
    assert res["valid"] is True
    assert res["risk_distance"] == 5.0
    assert res["reward_distance"] == 10.0
    assert res["rr_ratio"] == 2.0


def test_3_invalid_short_tp_inversion():
    """
    Test 3: Invalid SHORT TP inversion (reproducing the real XAUUSD failure).
    Entry = 4100.81, SL = 4105.59, TP = 4124.33.
    """
    res = DeterministicAIProvider.validate_trade_geometry(
        action="SELL LIMIT",
        entry_price=4100.81,
        stop_loss=4105.59,
        take_profit=4124.33,
    )
    assert res["valid"] is False
    assert "Invalid SHORT geometry" in res["reason"]
    assert "TP (4124.33) must be strictly less than Entry (4100.81)" in res["reason"]
    assert res["rr_ratio"] == 0.0


def test_4_invalid_long_tp_inversion():
    """Test 4: Invalid LONG TP inversion."""
    res = DeterministicAIProvider.validate_trade_geometry(
        action="BUY LIMIT",
        entry_price=4100.0,
        stop_loss=4095.0,
        take_profit=4080.0,
    )
    assert res["valid"] is False
    assert "Invalid LONG geometry" in res["reason"]
    assert "TP (4080.00) must be strictly greater than Entry (4100.00)" in res["reason"]
    assert res["rr_ratio"] == 0.0


def test_5_zero_and_negative_risk():
    """Test 5: Zero/negative risk geometries."""
    # LONG: Entry == SL (risk = 0)
    res_long_zero = DeterministicAIProvider.validate_trade_geometry(
        action="BUY LIMIT",
        entry_price=4100.0,
        stop_loss=4100.0,
        take_profit=4110.0,
    )
    assert res_long_zero["valid"] is False
    assert "SL (4100.00) must be strictly less than Entry (4100.00)" in res_long_zero["reason"]

    # SHORT: SL < Entry (negative risk)
    res_short_neg = DeterministicAIProvider.validate_trade_geometry(
        action="SELL LIMIT",
        entry_price=4100.0,
        stop_loss=4095.0,
        take_profit=3990.0,
    )
    assert res_short_neg["valid"] is False
    assert "SL (4095.00) must be strictly greater than Entry (4100.00)" in res_short_neg["reason"]


def test_6_rr_must_not_use_abs():
    """
    Test 6: R:R must not use abs() to validate inverted TP.
    SHORT: Entry = 4100, SL = 4105, TP = 4110.
    With abs(), reward would be abs(4100 - 4110) = 10, risk = 5 -> R:R = 2.0.
    Directionally, reward is 4100 - 4110 = -10 <= 0 -> Invalid.
    """
    res = DeterministicAIProvider.validate_trade_geometry(
        action="SELL LIMIT",
        entry_price=4100.0,
        stop_loss=4105.0,
        take_profit=4110.0,
    )
    assert res["valid"] is False
    assert res["rr_ratio"] != 2.0
    assert res["rr_ratio"] == 0.0
    assert "reward_distance" in res
    assert res["reward_distance"] < 0 or not res["valid"]


def test_finite_price_validation():
    """Trade geometry validator must reject inf and nan."""
    res_inf = DeterministicAIProvider.validate_trade_geometry(
        action="BUY LIMIT",
        entry_price=float("inf"),
        stop_loss=4095.0,
        take_profit=4110.0,
    )
    assert res_inf["valid"] is False
    assert "Non-finite" in res_inf["reason"]

    res_nan = DeterministicAIProvider.validate_trade_geometry(
        action="SELL LIMIT",
        entry_price=4100.0,
        stop_loss=float("nan"),
        take_profit=4090.0,
    )
    assert res_nan["valid"] is False
    assert "Non-finite" in res_nan["reason"]


@pytest.mark.asyncio
async def test_7_most_recent_sweep_selection():
    """
    Test 7: The most recent relevant sweep must be selected deterministically based on timestamp,
    regardless of list order.
    """
    provider = DeterministicAIProvider()
    t_older = "2026-10-08T08:00:00Z"
    t_newer = "2026-10-08T09:00:00Z"

    # Multiple high sweeps: older is placed FIRST, newer is placed SECOND
    sweeps_high = [
        {
            "level_type": "SWING_HIGH",
            "sweep_candle_ts": t_older,
            "extreme_price": 4110.0,
            "rejection_wick_ratio": 0.5,
            "is_exhaustion_candle": True,
        },
        {
            "level_type": "SESSION_HIGH",
            "sweep_candle_ts": t_newer,
            "extreme_price": 4125.0,
            "rejection_wick_ratio": 0.45,
            "is_exhaustion_candle": True,
        },
    ]

    mock_context_high = {
        "symbol": "XAUUSD",
        "current_price": 4115.0,
        "recent_liquidity_sweeps": sweeps_high,
        "market_structure": {"recent_mss": [], "active_unmitigated_fvgs": []},
        "session_state": {"session_levels": {}},
    }

    res_high = await provider.analyze(mock_context_high, "Look for high sweep rejection")
    # Should identify SESSION_HIGH (4125.0), not SWING_HIGH (4110.0)
    conds = [c.evidence for c in res_high.condition_breakdown if "Buy-Side Liquidity Swept" in c.condition]
    assert len(conds) == 1
    assert "4125.00" in conds[0]

    # Multiple low sweeps: newer is placed FIRST, older is placed SECOND
    sweeps_low = [
        {
            "level_type": "SWING_LOW_NEWER",
            "sweep_candle_ts": t_newer,
            "extreme_price": 4080.0,
            "rejection_wick_ratio": 0.5,
            "is_exhaustion_candle": True,
        },
        {
            "level_type": "SWING_LOW_OLDER",
            "sweep_candle_ts": t_older,
            "extreme_price": 4070.0,
            "rejection_wick_ratio": 0.4,
            "is_exhaustion_candle": True,
        },
    ]

    mock_context_low = {
        "symbol": "XAUUSD",
        "current_price": 4090.0,
        "recent_liquidity_sweeps": sweeps_low,
        "market_structure": {"recent_mss": [], "active_unmitigated_fvgs": []},
        "session_state": {"session_levels": {}},
    }

    res_low = await provider.analyze(mock_context_low, "Look for low sweep rejection")
    conds_low = [c.evidence for c in res_low.condition_breakdown if "Sell-Side Liquidity Swept" in c.condition]
    assert len(conds_low) == 1
    assert "4080.00" in conds_low[0]


@pytest.mark.asyncio
async def test_8_dual_sweep_conflict_handling():
    """
    Test 8: Dual sweep condition handling.
    - Newer LOW sweep must NOT be suppressed by older HIGH sweep.
    - Newer HIGH sweep must NOT be suppressed by older LOW sweep.
    - Equal timestamp HIGH + LOW sweeps must result in conflict/ambiguity.
    """
    provider = DeterministicAIProvider()
    t_older = "2026-10-08T08:00:00Z"
    t_newer = "2026-10-08T09:00:00Z"

    # Case A: Older HIGH sweep, newer LOW sweep
    context_bullish_recency = {
        "symbol": "EURUSD",
        "current_price": 1.0850,
        "recent_liquidity_sweeps": [
            {
                "level_type": "ASIAN_HIGH",
                "sweep_candle_ts": t_older,
                "extreme_price": 1.0890,
                "rejection_wick_ratio": 0.4,
                "is_exhaustion_candle": True,
            },
            {
                "level_type": "LONDON_LOW",
                "sweep_candle_ts": t_newer,
                "extreme_price": 1.0820,
                "rejection_wick_ratio": 0.4,
                "is_exhaustion_candle": True,
            },
        ],
        "market_structure": {"recent_mss": [], "active_unmitigated_fvgs": []},
        "session_state": {"session_levels": {}},
    }

    res_a = await provider.analyze(context_bullish_recency, "Trade session sweeps")
    # Must prioritize BULLISH branch because LOW sweep is newer
    assert any("Sell-Side Liquidity Swept" in c.condition for c in res_a.condition_breakdown)
    assert any("Dual Sweep Recency Resolution" in c.condition and "Bullish direction prioritized" in c.evidence for c in res_a.condition_breakdown)

    # Case B: Older LOW sweep, newer HIGH sweep
    context_bearish_recency = {
        "symbol": "EURUSD",
        "current_price": 1.0850,
        "recent_liquidity_sweeps": [
            {
                "level_type": "LONDON_LOW",
                "sweep_candle_ts": t_older,
                "extreme_price": 1.0820,
                "rejection_wick_ratio": 0.4,
                "is_exhaustion_candle": True,
            },
            {
                "level_type": "ASIAN_HIGH",
                "sweep_candle_ts": t_newer,
                "extreme_price": 1.0890,
                "rejection_wick_ratio": 0.4,
                "is_exhaustion_candle": True,
            },
        ],
        "market_structure": {"recent_mss": [], "active_unmitigated_fvgs": []},
        "session_state": {"session_levels": {}},
    }

    res_b = await provider.analyze(context_bearish_recency, "Trade session sweeps")
    # Must prioritize BEARISH branch because HIGH sweep is newer
    assert any("Buy-Side Liquidity Swept" in c.condition for c in res_b.condition_breakdown)
    assert any("Dual Sweep Recency Resolution" in c.condition and "Bearish direction prioritized" in c.evidence for c in res_b.condition_breakdown)

    # Case C: Identical timestamp dual sweep -> Ambiguous conflict
    context_conflict = {
        "symbol": "EURUSD",
        "current_price": 1.0850,
        "recent_liquidity_sweeps": [
            {
                "level_type": "ASIAN_HIGH",
                "sweep_candle_ts": t_newer,
                "extreme_price": 1.0890,
                "rejection_wick_ratio": 0.4,
                "is_exhaustion_candle": True,
            },
            {
                "level_type": "ASIAN_LOW",
                "sweep_candle_ts": t_newer,
                "extreme_price": 1.0820,
                "rejection_wick_ratio": 0.4,
                "is_exhaustion_candle": True,
            },
        ],
        "market_structure": {"recent_mss": [], "active_unmitigated_fvgs": []},
        "session_state": {"session_levels": {}},
    }

    res_c = await provider.analyze(context_conflict, "Trade session sweeps")
    assert res_c.state != AnalysisStateEnum.VALID_SETUP
    assert any("Directional Sweep & Market Structure Alignment" in c.condition and not c.satisfied for c in res_c.condition_breakdown)
    assert any("dual sweep conflict" in a.text_snippet.lower() for a in res_c.ambiguities_detected)


@pytest.mark.asyncio
async def test_11_xauusd_forensic_regression():
    """
    Test 11: Exact forensic regression reproducing the XAUUSD investigation failure:
    Instrument: XAUUSD
    Action: SELL LIMIT
    Entry: 4100.81
    SL: 4105.59
    TP: 4124.33
    Expected: Candidate MUST be rejected and can NEVER receive VALID_SETUP.
    Explicitly proves that Entry < SL < TP is invalid for SHORT.
    """
    provider = DeterministicAIProvider()

    # Direct validation check
    geom_check = provider.validate_trade_geometry(
        action="SELL LIMIT",
        entry_price=4100.81,
        stop_loss=4105.59,
        take_profit=4124.33,
    )
    assert geom_check["valid"] is False
    assert "Invalid SHORT geometry" in geom_check["reason"]
    assert "TP (4124.33) must be strictly less than Entry (4100.81)" in geom_check["reason"]

    # End-to-end provider execution check:
    # Setup conditions that would otherwise pass all filters (exhaustion, MSS, FVG)
    # but where an inverted opposing level (4124.33) exists or is probed.
    mock_xau_context = {
        "symbol": "XAUUSD",
        "current_price": 4102.0,
        "recent_liquidity_sweeps": [
            {
                "level_type": "SESSION_HIGH",
                "sweep_candle_ts": "2026-10-08T09:30:00Z",
                "extreme_price": 4104.09,  # With buffer (1.50) -> SL ~ 4105.59
                "rejection_wick_ratio": 0.45,
                "is_exhaustion_candle": True,
                "sweep_depth_pips": 15.0,
            }
        ],
        "market_structure": {
            "recent_mss": [
                {
                    "mss_type": "BEARISH",
                    "broken_swing_price": 4099.0,
                    "shift_candle_ts": "2026-10-08T09:32:00Z",
                }
            ],
            "active_unmitigated_fvgs": [
                {
                    "fvg_type": "BEARISH",
                    "top_price": 4101.81,
                    "bottom_price": 4099.81,  # midpoint = 4100.81
                    "mitigated": False,
                }
            ],
        },
        "session_state": {
            "session_levels": {
                "asian": {
                    "high": 4124.33,
                    "low": 4124.33,
                }
            }
        },
        "candidate_take_profit": 4124.33,  # Candidate target attempting to place TP above entry on SHORT
    }

    result = await provider.analyze(mock_xau_context, "London 3-step setup")

    # Critical requirement: MUST NEVER return VALID_SETUP
    assert result.state != AnalysisStateEnum.VALID_SETUP
    assert result.state == AnalysisStateEnum.POTENTIAL_SETUP

    # Diagnostic check: reason must explicitly identify the trade geometry violation
    cond_map = {c.condition: c for c in result.condition_breakdown}
    assert "Trade Geometry Valid (TP < Entry < SL)" in cond_map
    assert cond_map["Trade Geometry Valid (TP < Entry < SL)"].satisfied is False
    assert "Trade geometry invalid" in cond_map["Trade Geometry Valid (TP < Entry < SL)"].evidence
    assert "4100.81" in cond_map["Trade Geometry Valid (TP < Entry < SL)"].evidence
    assert "4124.33" in cond_map["Trade Geometry Valid (TP < Entry < SL)"].evidence
    assert "Trade geometry invalid" in result.summary


@pytest.mark.asyncio
async def test_session_profile_model_conditions():
    """Verify London session sweeping Asia low with Bullish 7H bias produces MET for 7H bias, session range, sweep."""
    provider = DeterministicAIProvider()

    context = {
        "symbol": "EURUSD",
        "instrument_id": 1,
        "timeframe": "15m",
        "current_price": 1.0845,
        "active_session": "london",
        "seven_hour_profile": {
            "status": "COMPLETED",
            "direction": "BULLISH",
            "classification": "EXPANSION",
        },
        "session_state": {
            "session_levels": {
                "asian": {
                    "high": 1.0880,
                    "low": 1.0820,
                    "swept_low": True,
                    "swept_high": False,
                }
            }
        },
        "market_structure": {
            "recent_mss": [
                {
                    "mss_type": "BULLISH",
                    "broken_swing_price": 1.0835,
                    "shift_candle_ts": "2026-10-08T09:30:00Z",
                }
            ],
            "active_unmitigated_fvgs": [
                {
                    "fvg_type": "BULLISH",
                    "top_price": 1.0830,
                    "bottom_price": 1.0825,
                    "mitigated": False,
                }
            ],
        },
        "liquidity": {
            "sweeps": [
                {
                    "sweep_type": "BULLISH",
                    "swept_level_price": 1.0820,
                    "sweep_depth_pips": 5.0,
                    "rejection_wick_ratio": 0.40,
                }
            ]
        },
    }

    result = await provider.analyze(context, "London 3-step setup")

    cond_map = {c.condition: c for c in result.condition_breakdown}
    assert "7H bias" in cond_map
    assert cond_map["7H bias"].satisfied is True
    assert "Prior session range available" in cond_map
    assert cond_map["Prior session range available"].satisfied is True
    assert "Sweep in active session" in cond_map
    assert cond_map["Sweep in active session"].satisfied is True


@pytest.mark.asyncio
async def test_session_proximity_potential_setup():
    """Verify price approaching Asian low in London returns POTENTIAL_SETUP before sweep has occurred."""
    provider = DeterministicAIProvider()

    context = {
        "symbol": "EURUSD",
        "instrument_id": 1,
        "timeframe": "15m",
        "current_price": 1.0825, # Asian low is 1.0820, distance = 5 pips (< 10 pips threshold)
        "active_session": "london",
        "seven_hour_profile": {
            "status": "COMPLETED",
            "direction": "BULLISH",
        },
        "session_state": {
            "session_levels": {
                "asian": {
                    "high": 1.0880,
                    "low": 1.0820,
                    "swept_low": False, # Not yet swept
                    "swept_high": False,
                }
            }
        },
        "market_structure": {},
        "liquidity": {"sweeps": []},
    }

    result = await provider.analyze(context, "London 3-step setup")
    assert result.state == AnalysisStateEnum.POTENTIAL_SETUP
    assert "approaching" in result.summary.lower()



def test_scanner_state_counts_in_status():
    """Verify scanner get_status() includes state_counts dictionary with required state keys."""
    from app.services.ai.session_scanner import SessionScannerWorker
    worker = SessionScannerWorker()
    worker._last_state_counts = {
        "NO_SETUP": 5,
        "WATCH": 2,
        "POTENTIAL": 1,
        "VALID": 1,
    }
    status = worker.get_status()
    assert "state_counts" in status
    assert status["state_counts"]["NO_SETUP"] == 5
    assert status["state_counts"]["WATCH"] == 2
    assert status["state_counts"]["POTENTIAL"] == 1
    assert status["state_counts"]["VALID"] == 1


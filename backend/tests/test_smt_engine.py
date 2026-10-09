import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.database import get_db
from app.schemas.candle import CandleRead
from app.schemas import SMTDivergenceType, SMTPairGroup, SMTContext
from app.services.features import SMTEngine
from app.services.bias.bias_validation_engine import BiasValidationEngine, FinalBiasState, BiasQuality

def make_candle(ts: int, open_: float, high: float, low: float, close: float) -> CandleRead:
    return CandleRead(
        id=ts,
        instrument_id=1,
        timeframe="15m",
        timestamp_utc=datetime.fromtimestamp(ts, tz=timezone.utc),
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=100.0,
        provider="deriv",
        is_complete=True,
    )

def test_smt_metals_asian_low_sweep_bullish_divergence():
    """
    Verifies that when XAGUSD sweeps Asian Low but XAUUSD holds a Higher Low,
    a BULLISH_SMT divergence is generated with XAUUSD as the strong asset.
    """
    session_xau = {
        "asian": {"swept_low": False, "swept_high": False}
    }
    session_xag = {
        "asian": {"swept_low": True, "swept_high": False}
    }

    result = SMTEngine.detect_divergence_from_session_levels(
        symbol_a="XAUUSD",
        session_levels_a=session_xau,
        symbol_b="XAGUSD",
        session_levels_b=session_xag,
        session_name="asian",
        pair_group=SMTPairGroup.METALS,
    )

    assert result is not None
    assert result.divergence_type == SMTDivergenceType.BULLISH_SMT
    assert result.swept_symbol == "XAGUSD"
    assert result.strong_symbol == "XAUUSD"
    assert result.reference_level == "ASIAN_LOW"
    assert "Higher Low" in result.summary

def test_smt_metals_asian_high_sweep_bearish_divergence():
    """
    Verifies that when XAGUSD sweeps Asian High but XAUUSD forms a Lower High,
    a BEARISH_SMT divergence is generated.
    """
    session_xau = {
        "asian": {"swept_low": False, "swept_high": False}
    }
    session_xag = {
        "asian": {"swept_low": False, "swept_high": True}
    }

    result = SMTEngine.detect_divergence_from_session_levels(
        symbol_a="XAUUSD",
        session_levels_a=session_xau,
        symbol_b="XAGUSD",
        session_levels_b=session_xag,
        session_name="asian",
        pair_group=SMTPairGroup.METALS,
    )

    assert result is not None
    assert result.divergence_type == SMTDivergenceType.BEARISH_SMT
    assert result.swept_symbol == "XAGUSD"
    assert result.strong_symbol == "XAUUSD"
    assert result.reference_level == "ASIAN_HIGH"

def test_smt_majors_eurusd_gbpusd_bullish_divergence():
    """
    Verifies that when EURUSD sweeps London low but GBPUSD holds higher low,
    a BULLISH_SMT divergence is detected.
    """
    session_eur = {
        "london": {"swept_low": True, "swept_high": False}
    }
    session_gbp = {
        "london": {"swept_low": False, "swept_high": False}
    }

    result = SMTEngine.detect_divergence_from_session_levels(
        symbol_a="EURUSD",
        session_levels_a=session_eur,
        symbol_b="GBPUSD",
        session_levels_b=session_gbp,
        session_name="london",
        pair_group=SMTPairGroup.MAJORS,
    )

    assert result is not None
    assert result.divergence_type == SMTDivergenceType.BULLISH_SMT
    assert result.swept_symbol == "EURUSD"
    assert result.strong_symbol == "GBPUSD"

def test_smt_symmetric_action_yields_none():
    """
    Verifies that when both pairs sweep or neither sweeps, no divergence is declared.
    """
    # Both swept low
    res1 = SMTEngine.detect_divergence_from_session_levels(
        symbol_a="XAUUSD",
        session_levels_a={"asian": {"swept_low": True, "swept_high": False}},
        symbol_b="XAGUSD",
        session_levels_b={"asian": {"swept_low": True, "swept_high": False}},
    )
    assert res1 is None

    # Neither swept
    res2 = SMTEngine.detect_divergence_from_session_levels(
        symbol_a="XAUUSD",
        session_levels_a={"asian": {"swept_low": False, "swept_high": False}},
        symbol_b="XAGUSD",
        session_levels_b={"asian": {"swept_low": False, "swept_high": False}},
    )
    assert res2 is None

def test_smt_candle_swing_bullish_divergence():
    """
    Verifies candle-level SMT detection when XAGUSD breaks to a lower low
    while XAUUSD holds a higher low.
    """
    # Base timestamp
    t = 1700000000

    # 10 anchor candles followed by 10 test candles
    # Anchor candles: low around 100 for XAG, 2000 for XAU
    candles_xag = [make_candle(t + i * 900, 105, 108, 100, 104) for i in range(8)]
    candles_xau = [make_candle(t + i * 900, 2010, 2015, 2000, 2008) for i in range(8)]

    # Test candles: XAG breaks below 100 (low=98) -> Lower Low
    candles_xag.extend([make_candle(t + (8 + i) * 900, 103, 106, 98 if i == 2 else 101, 103) for i in range(8)])

    # XAU test candles: Low holds at 2005 (above 2000) -> Higher Low
    candles_xau.extend([make_candle(t + (8 + i) * 900, 2008, 2020, 2005, 2018) for i in range(8)])

    result = SMTEngine.detect_divergence_from_candles(
        symbol_a="XAUUSD",
        candles_a=candles_xau,
        symbol_b="XAGUSD",
        candles_b=candles_xag,
        lookback=16,
        pair_group=SMTPairGroup.METALS,
    )

    assert result is not None
    assert result.divergence_type == SMTDivergenceType.BULLISH_SMT
    assert result.swept_symbol == "XAGUSD"
    assert result.strong_symbol == "XAUUSD"

def test_smt_confluence_elevates_bias_quality_to_a_plus():
    """
    Verifies that BiasValidationEngine elevates bias quality to A_PLUS
    when supported by aligned SMT divergence.
    """
    smt_data = {
        "has_smt_divergence": True,
        "confluence_bias": "BULLISH",
        "active_divergence": {
            "summary": "Bullish SMT Divergence: XAGUSD swept low while XAUUSD held higher low.",
            "divergence_type": "BULLISH_SMT",
        }
    }

    res = BiasValidationEngine.validate_bias(
        symbol="XAUUSD",
        custom_htf={"tf_4h_trend": "BULLISH", "tf_1h_trend": "BULLISH"},
        custom_7h={"direction": "BULLISH", "classification": "NORMAL"},
        custom_15m={"trend": "BULLISH"},
        smt_data=smt_data,
    )

    assert res.final_bias == FinalBiasState.BULLISH
    assert res.bias_quality == BiasQuality.A_PLUS
    assert "Confirmed by institutional Bullish SMT Divergence" in res.explanation
    assert res.smt_context.get("has_smt_divergence") is True

def test_smt_contradiction_flags_conflict_in_bias_engine():
    """
    Verifies that BiasValidationEngine records a conflict when SMT divergence
    contradicts the higher-timeframe technical bias.
    """
    smt_data = {
        "has_smt_divergence": True,
        "confluence_bias": "BEARISH",
        "active_divergence": {
            "summary": "Bearish SMT Divergence: XAGUSD swept high while XAUUSD formed lower high.",
            "divergence_type": "BEARISH_SMT",
        }
    }

    res = BiasValidationEngine.validate_bias(
        symbol="XAUUSD",
        custom_htf={"tf_4h_trend": "BULLISH", "tf_1h_trend": "BULLISH"},
        custom_7h={"direction": "BULLISH", "classification": "NORMAL"},
        smt_data=smt_data,
    )

    assert any("SMT divergence (BEARISH) contradicts structural bias (BULLISH)" in c for c in res.conflicts)

@pytest.mark.asyncio
async def test_smt_api_endpoints(db_session):
    """
    Verifies FastAPI SMT endpoints:
    - GET /api/v1/smt/divergence?symbol=XAUUSD
    - GET /api/v1/smt/matrix
    """
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Single symbol SMT check
        res = await client.get("/api/v1/smt/divergence?symbol=XAUUSD")
        assert res.status_code == 200
        data = res.json()
        assert data["symbol"] == "XAUUSD"
        assert data["correlated_symbol"] == "XAGUSD"
        assert "has_smt_divergence" in data

        # 2. Matrix SMT check
        res_mat = await client.get("/api/v1/smt/matrix")
        assert res_mat.status_code == 200
        mat = res_mat.json()
        assert len(mat) >= 2
        symbols_in_mat = [item["symbol"] for item in mat]
        assert "XAUUSD" in symbols_in_mat
        assert "EURUSD" in symbols_in_mat

    app.dependency_overrides.clear()

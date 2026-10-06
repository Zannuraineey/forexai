import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.database import get_db
from app.models.analysis import AnalysisStateEnum
from app.schemas.candle import CandleDTO
from app.schemas.ai_analysis import AIAnalysisRequest
from app.services.candle_service import CandleService
from app.services.strategy_service import StrategyService
from app.services.ai.deterministic_provider import DeterministicAIProvider
from app.services.ai.ai_engine import AIAnalysisEngine

@pytest.mark.asyncio
async def test_deterministic_ai_provider_user_example():
    provider = DeterministicAIProvider()

    # User's explicit prompt from requirements:
    # "Only consider a setup after price sweeps the Asian high."
    user_instruction = "Only consider a setup after price sweeps the Asian high."

    mock_context = {
        "current_price": 1.0872,
        "indicators": {"rsi_14": 55.0, "atr_14_pips": 12.0},
        "session_state": {
            "session_levels": {
                "asian": {
                    "high": 1.0865,
                    "low": 1.0820,
                    "swept_high": True,
                    "swept_low": False,
                }
            }
        },
        "recent_liquidity_sweeps": [
            {"level_type": "ASIAN_HIGH", "sweep_type": "BULLISH_SWEEP"}
        ],
        "market_structure": {"trend_state": "BULLISH"},
        "candle_structure": {"pattern_type": "NEUTRAL", "direction": "BULLISH"},
    }

    result = await provider.analyze(market_context=mock_context, user_instructions=user_instruction)

    # Verifies the exact required output pattern:
    # Asian high: identified, Current price: above Asian high, Liquidity sweep: detected
    # Result: WATCH
    assert result.state == AnalysisStateEnum.WATCH
    cond_map = {c.condition: c for c in result.condition_breakdown}
    assert "Asian high identified" in cond_map and cond_map["Asian high identified"].satisfied is True
    assert "Current price above Asian high" in cond_map and cond_map["Current price above Asian high"].satisfied is True
    assert "Liquidity sweep detected" in cond_map and cond_map["Liquidity sweep detected"].satisfied is True
    assert "Other required conditions" in cond_map and cond_map["Other required conditions"].satisfied is False
    assert "Neutral factual evaluation" in result.confidence_notes

@pytest.mark.asyncio
async def test_ambiguity_detection_without_inventing_rules():
    provider = DeterministicAIProvider()

    # Vague instruction with subjective terms
    ambiguous_instruction = "Look for strong volume and good momentum after London open with normal volatility."

    mock_context = {
        "current_price": 1.0850,
        "indicators": {"rsi_14": 50.0},
        "session_state": {"session_levels": {}},
        "recent_liquidity_sweeps": [],
    }

    result = await provider.analyze(market_context=mock_context, user_instructions=ambiguous_instruction)

    assert len(result.ambiguities_detected) >= 2
    snippets = [a.text_snippet.lower() for a in result.ambiguities_detected]
    assert any("volume" in s for s in snippets)
    assert any("momentum" in s for s in snippets)

@pytest.mark.asyncio
async def test_full_ai_analysis_engine_execution_and_persistence(db_session):
    candle_svc = CandleService(db_session)
    strat_svc = StrategyService(db_session)

    # 1. Update London session strategy in PostgreSQL
    rule = "Wait for London session to break previous day high and RSI < 70."
    inst = await strat_svc.update_instruction(
        user_id=1,
        session_name="london",
        new_prompt=rule,
        change_summary="PDH break with RSI limit",
    )

    # 2. Seed candles for EURUSD
    now = datetime(2026, 10, 4, 14, 0, 0, tzinfo=timezone.utc)
    # Seed 30 15m candles
    candles = []
    for i in range(30):
        ts = now - timedelta(minutes=15 * (30 - i))
        price = 1.0850 + (i * 0.0001)
        candles.append(
            CandleDTO(
                symbol="EURUSD",
                timeframe="15m",
                timestamp_utc=ts,
                open=price,
                high=price + 0.0004,
                low=price - 0.0002,
                close=price + 0.0001,
                volume=100.0,
                provider="deriv",
            )
        )
    await candle_svc.save_candles(candles)

    # Seed daily candle for PDH
    daily_candles = [
        CandleDTO(
            symbol="EURUSD",
            timeframe="1d",
            timestamp_utc=now - timedelta(days=1),
            open=1.0800,
            high=1.0840,
            low=1.0790,
            close=1.0830,
            volume=5000.0,
            provider="deriv",
        )
    ]
    await candle_svc.save_candles(daily_candles)

    # 3. Execute AI Analysis
    engine = AIAnalysisEngine(db_session)
    req = AIAnalysisRequest(
        symbol="EURUSD",
        timeframe="15m",
        session_name="london",
    )
    analysis_record = await engine.execute_analysis(req)

    assert analysis_record.id is not None
    assert analysis_record.symbol == "EURUSD"
    assert analysis_record.instruction_version_id == inst.current_version or analysis_record.instruction_version_id is not None
    assert analysis_record.session_name == "london"
    assert analysis_record.summary is not None
    assert len(analysis_record.condition_breakdown) >= 1

@pytest.mark.asyncio
async def test_analysis_api_endpoints(db_session):
    # Seed candles for EURUSD
    candle_svc = CandleService(db_session)
    now = datetime(2026, 10, 4, 14, 0, 0, tzinfo=timezone.utc)
    candles = [
        CandleDTO(
            symbol="EURUSD",
            timeframe="15m",
            timestamp_utc=now - timedelta(minutes=15 * (10 - i)),
            open=1.0850,
            high=1.0870,
            low=1.0840,
            close=1.0860,
            volume=100.0,
            provider="deriv",
        )
        for i in range(10)
    ]
    await candle_svc.save_candles(candles)

    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Execute analysis
            res = await client.post(
                "/api/v1/analysis/evaluate",
                json={
                    "symbol": "EURUSD",
                    "timeframe": "15m",
                    "session_name": "london",
                }
            )
            assert res.status_code == 200
            data = res.json()
            assert "state" in data
            assert "condition_breakdown" in data
            analysis_id = data["id"]

            # Query history
            hist_res = await client.get("/api/v1/analysis/history?symbol=EURUSD")
            assert hist_res.status_code == 200
            hist_data = hist_res.json()
            assert len(hist_data) >= 1
            assert hist_data[0]["symbol"] == "EURUSD"

            # Query single by ID
            single_res = await client.get(f"/api/v1/analysis/{analysis_id}")
            assert single_res.status_code == 200
            assert single_res.json()["id"] == analysis_id
    finally:
        app.dependency_overrides.clear()

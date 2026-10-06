import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.strategy_service import StrategyService

@pytest.mark.asyncio
async def test_strategy_service_initialization_and_versioning(db_session):
    service = StrategyService(db_session)

    # 1. Fetch default instruction (should create v1)
    asian_inst = await service.get_or_create_instruction(user_id=1, session_name="asian")
    assert asian_inst.current_version == 1
    assert asian_inst.is_enabled is True

    # 2. Update instruction with new natural-language rule
    custom_rule = "Only look for longs if Asian high was swept during London open and 15m RSI < 40."
    updated = await service.update_instruction(
        user_id=1,
        session_name="asian",
        new_prompt=custom_rule,
        change_summary="Added Asian sweep + RSI constraint",
    )
    assert updated.current_version == 2

    # 3. Check version history
    history = await service.get_instruction_history(user_id=1, session_name="asian")
    assert len(history) == 2
    assert history[0].version == 2
    assert history[0].prompt_content == custom_rule
    assert history[1].version == 1

    # 4. Rollback to v1
    rolled_back = await service.rollback_to_version(
        user_id=1,
        session_name="asian",
        target_version=1,
        reason="Testing rollback",
    )
    assert rolled_back.current_version == 3
    active_v = await service.get_active_version(rolled_back.id, 3)
    v1 = await service.get_active_version(rolled_back.id, 1)
    assert active_v.prompt_content == v1.prompt_content

from app.core.database import get_db

@pytest.mark.asyncio
async def test_strategy_api_endpoints(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Get all session configs
            res = await client.get("/api/v1/strategy/sessions")
            assert res.status_code == 200
            data = res.json()
            assert "asian" in data
            assert "london" in data
            assert "new_york" in data
            assert data["london"]["enabled"] is True

            # 2. Update London session strategy
            new_instruction = "Wait for London breakout of previous day high before considering continuation."
            put_res = await client.put(
                "/api/v1/strategy/sessions/london",
                json={
                    "instructions": new_instruction,
                    "change_summary": "Initial London breakout rule",
                }
            )
            assert put_res.status_code == 200
            put_data = put_res.json()
            assert put_data["current_version"] == 2
            assert put_data["active_prompt"] == new_instruction

            # 3. Fetch history
            hist_res = await client.get("/api/v1/strategy/sessions/london/history")
            assert hist_res.status_code == 200
            hist_data = hist_res.json()
            assert len(hist_data) == 2
            assert hist_data[0]["version"] == 2
            assert hist_data[0]["prompt_content"] == new_instruction

            # 4. Rollback via API
            rb_res = await client.post(
                "/api/v1/strategy/sessions/london/rollback",
                json={"target_version": 1, "reason": "Reverting breakout rule"}
            )
            assert rb_res.status_code == 200
            rb_data = rb_res.json()
            assert rb_data["current_version"] == 3
    finally:
        app.dependency_overrides.clear()

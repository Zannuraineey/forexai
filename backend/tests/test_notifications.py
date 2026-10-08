import pytest
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.database import get_db
from app.models.analysis import AnalysisStateEnum
from app.schemas.ai_analysis import AnalysisRecordRead
from app.schemas.notification import DeviceRegistrationRequest, NotificationRuleConfig
from app.services.notifications import NotificationService

@pytest.mark.asyncio
async def test_device_registration_and_notification_dispatch(db_session):
    svc = NotificationService(db_session)

    # 1. Register device
    dev_req = DeviceRegistrationRequest(
        fcm_token="sample-fcm-token-12345",
        device_platform="android",
        user_id=1,
    )
    dev = await svc.register_device(dev_req)
    assert dev.id is not None
    assert dev.fcm_token == "sample-fcm-token-12345"

    # 2. Case A: NO_SETUP -> Notification should NOT be dispatched
    no_setup_analysis = AnalysisRecordRead(
        id=101,
        symbol="EURUSD",
        instrument_id=1,
        timeframe="15m",
        timestamp_utc=datetime.now(timezone.utc),
        session_name="london",
        model_version="test-v1",
        state=AnalysisStateEnum.NO_SETUP,
        summary="No conditions met.",
        condition_breakdown=[],
        ambiguities_detected=[],
        created_at=datetime.now(timezone.utc),
    )
    notif_none = await svc.evaluate_and_dispatch(no_setup_analysis, user_id=1)
    assert notif_none is None

    # 3. Case B: VALID_SETUP -> Notification should be dispatched
    valid_analysis = AnalysisRecordRead(
        id=102,
        symbol="EURUSD",
        instrument_id=1,
        timeframe="15m",
        timestamp_utc=datetime.now(timezone.utc),
        session_name="london",
        model_version="test-v1",
        state=AnalysisStateEnum.VALID_SETUP,
        summary="Valid breakout confirmed with all conditions satisfied.",
        condition_breakdown=[],
        ambiguities_detected=[],
        created_at=datetime.now(timezone.utc),
    )
    notif = await svc.evaluate_and_dispatch(valid_analysis, user_id=1)
    assert notif is not None
    assert notif.status in ["SENT", "SENT_SIMULATED"]
    assert "EURUSD" in notif.title

    # 4. Deduplication: immediate duplicate should be suppressed
    duplicate_notif = await svc.evaluate_and_dispatch(valid_analysis, user_id=1)
    assert duplicate_notif is None

@pytest.mark.asyncio
async def test_notification_api_endpoints(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Register device
            reg_res = await client.post(
                "/api/v1/devices/register",
                json={
                    "fcm_token": "client-token-abc-987",
                    "device_platform": "ios",
                    "user_id": 1,
                }
            )
            assert reg_res.status_code == 200
            assert reg_res.json()["device_platform"] == "ios"

            # Query settings
            settings_res = await client.get("/api/v1/notifications/settings")
            assert settings_res.status_code == 200
            assert settings_res.json()["notify_on_valid_setup"] is True

            # Trigger test dispatch
            dispatch_res = await client.post("/api/v1/notifications/test-dispatch?symbol=GBPUSD")
            assert dispatch_res.status_code == 200
            data = dispatch_res.json()
            assert data is not None
            assert data["status"] in ["SENT", "SENT_SIMULATED"]

            # Get notification logs
            list_res = await client.get("/api/v1/notifications")
            assert list_res.status_code == 200
            assert len(list_res.json()) >= 1

            # Test Trade Lifecycle Endpoint
            lifecycle_res = await client.post(
                "/api/v1/analysis/lifecycle-event",
                json={
                    "symbol": "XAUUSD",
                    "event_type": "TP1_HIT_MOVE_TO_BE",
                    "price": 2640.50,
                    "timeframe": "15m",
                    "action": "SELL LIMIT",
                    "details": "TP1 achieved, move SL to BE.",
                }
            )
            assert lifecycle_res.status_code == 200
            assert lifecycle_res.json()["status"] == "success"
            assert lifecycle_res.json()["event_type"] == "TP1_HIT_MOVE_TO_BE"
    finally:
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_structured_trade_setup_and_lifecycle_notifications(db_session):
    from app.schemas.ai_analysis import TradeSetup, TradeTarget, InvalidationRule
    svc = NotificationService(db_session)

    # 1. Register device
    await svc.register_device(DeviceRegistrationRequest(
        fcm_token="lifecycle-device-token",
        device_platform="android",
        user_id=1,
    ))

    # 2. Test VALID_SETUP with TradeSetup payload
    trade_setup = TradeSetup(
        action="SELL LIMIT",
        entry_price=2650.0,
        stop_loss=2655.0,
        take_profit=2635.0,
        risk_pips=50.0,
        targets={
            "tp1": TradeTarget(price=2642.5, rr=1.5, action="CLOSE_40_PERCENT_AND_MOVE_SL_TO_BE"),
            "tp2": TradeTarget(price=2635.0, rr=3.0, action="CLOSE_40_PERCENT_AT_LIQUIDITY"),
            "tp3": TradeTarget(price=2625.0, rr=5.0, action="TRAIL_20_PERCENT_RUNNER"),
        },
        invalidation=InvalidationRule(expiry_minutes=30, cancel_if_touched=2642.5),
        confluence=["Asian High Swept", "Judas Reversal Wick", "Displacement MSS"],
        grade="Grade A+",
        session="London Open",
        model="London 3-Step",
        rr_ratio=3.0,
        sl_buffer_pips=15.0,
    )

    analysis = AnalysisRecordRead(
        id=201,
        symbol="XAUUSD",
        instrument_id=1,
        timeframe="15m",
        timestamp_utc=datetime.now(timezone.utc),
        session_name="london",
        model_version="test-v1",
        state=AnalysisStateEnum.VALID_SETUP,
        summary="🎯 VALID SETUP [SELL LIMIT]: XAUUSD (Grade A+ • London Open).",
        condition_breakdown=[],
        ambiguities_detected=[],
        trade_setup=trade_setup,
        created_at=datetime.now(timezone.utc),
    )

    notif = await svc.evaluate_and_dispatch(analysis, user_id=1)
    assert notif is not None
    assert "SELL LIMIT" in notif.title
    assert "2650" in notif.body
    assert notif.payload["type"] == "TRADE_SETUP_ALERT"
    assert notif.payload["action"] == "SELL LIMIT"
    assert notif.payload["entry_price"] == "2650.0"

    # 3. Test Lifecycle Event: ENTRY_FILLED
    n_fill = await svc.dispatch_trade_lifecycle_update(
        symbol="XAUUSD",
        event_type="ENTRY_FILLED",
        price=2650.0,
        action="SELL LIMIT",
        user_id=1,
    )
    assert n_fill is not None
    assert "ORDER FILLED" in n_fill.title

    # 4. Test Lifecycle Event: TP1_HIT_MOVE_TO_BE
    n_tp1 = await svc.dispatch_trade_lifecycle_update(
        symbol="XAUUSD",
        event_type="TP1_HIT_MOVE_TO_BE",
        price=2642.5,
        user_id=1,
    )
    assert n_tp1 is not None
    assert "MOVE SL TO BREAK-EVEN" in n_tp1.title

    # 5. Test Lifecycle Event: SETUP_CANCELLED (front-run detection)
    n_cancel = await svc.dispatch_trade_lifecycle_update(
        symbol="XAUUSD",
        event_type="SETUP_CANCELLED",
        price=2642.5,
        user_id=1,
    )
    assert n_cancel is not None
    assert "CANCELLED" in n_cancel.title


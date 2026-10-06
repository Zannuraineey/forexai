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
    assert notif.status == "SENT"
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
            assert data["status"] == "SENT"

            # Get notification logs
            list_res = await client.get("/api/v1/notifications")
            assert list_res.status_code == 200
            assert len(list_res.json()) >= 1
    finally:
        app.dependency_overrides.clear()

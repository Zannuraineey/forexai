from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.notifications.notification_service import NotificationService
from app.schemas.notification import (
    DeviceRegistrationRequest,
    DeviceRead,
    NotificationRead,
    NotificationRuleConfig,
)
from app.schemas.ai_analysis import AnalysisRecordRead
from app.models.analysis import AnalysisStateEnum
from datetime import datetime, timezone

router = APIRouter(tags=["Notifications & Devices"])

@router.post("/devices/register", response_model=DeviceRead)
async def register_device(
    request: DeviceRegistrationRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Registers or updates an FCM device push token from the mobile application.
    """
    service = NotificationService(db)
    return await service.register_device(request)

@router.get("/notifications", response_model=List[NotificationRead])
async def get_notifications(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    Queries past notification logs and dispatch statuses.
    """
    service = NotificationService(db)
    return await service.get_notifications(user_id=1, limit=limit, offset=offset)

@router.get("/notifications/status")
async def get_notification_system_status(db: AsyncSession = Depends(get_db)):
    """
    Returns Firebase Admin SDK initialization status and device count.
    """
    from app.services.notifications.notification_service import _get_firebase_app
    from app.models.analysis import Device
    from sqlalchemy import select, func

    fb_app = _get_firebase_app()
    stmt = select(func.count(Device.id))
    res = await db.execute(stmt)
    active_devices = res.scalar() or 0

    return {
        "firebase_initialized": fb_app is not None,
        "active_devices_count": active_devices,
        "project_id": fb_app.project_id if fb_app else None,
        "mode": "LIVE_FCM" if fb_app else "SIMULATED (Set FIREBASE_SERVICE_ACCOUNT_BASE64 on Railway)",
    }

@router.get("/notifications/settings", response_model=NotificationRuleConfig)
async def get_notification_settings():
    """
    Returns current notification rule configuration.
    """
    return NotificationService.DEFAULT_CONFIG

@router.post("/notifications/test-dispatch", response_model=Optional[NotificationRead])
async def test_notification_dispatch(
    symbol: str = "EURUSD",
    timeframe: str = "15m",
    db: AsyncSession = Depends(get_db),
):
    """
    Triggers a test decoupled dispatch to registered mobile devices.
    """
    service = NotificationService(db)
    dummy_analysis = AnalysisRecordRead(
        id=99999,
        symbol=symbol.upper(),
        instrument_id=1,
        timeframe=timeframe,
        timestamp_utc=datetime.now(timezone.utc),
        session_name="london",
        model_version="test-v1",
        state=AnalysisStateEnum.VALID_SETUP,
        summary="Test notification: All strategy criteria met on test bar.",
        condition_breakdown=[],
        ambiguities_detected=[],
        created_at=datetime.now(timezone.utc),
    )
    return await service.evaluate_and_dispatch(dummy_analysis, user_id=1)

@router.post("/notifications/settings", response_model=NotificationRuleConfig)
async def update_notification_settings(config: NotificationRuleConfig):
    """
    Updates notification rule configuration including user-selected UT Bot pairs.
    """
    NotificationService.DEFAULT_CONFIG = config
    return NotificationService.DEFAULT_CONFIG

@router.post("/notifications/test-ut-bot", response_model=Optional[NotificationRead])
async def test_ut_bot_dispatch(
    symbol: str = "R_75",
    timeframe: str = "15m",
    signal: str = "BUY",
    db: AsyncSession = Depends(get_db),
):
    """
    Triggers an immediate test UT Bot push notification for a user-selected pair.
    """
    service = NotificationService(db)
    test_result = {
        "signal": signal.upper(),
        "current_price": 451.25,
        "trailing_stop": 448.10,
        "ema_200": 446.50,
        "rsi": 58.2,
    }
    cfg = NotificationService.DEFAULT_CONFIG.model_copy()
    cfg.cooldown_minutes = 0
    if symbol.upper() not in [p.upper() for p in cfg.ut_bot_pairs]:
        cfg.ut_bot_pairs.append(symbol.upper())
    return await service.dispatch_ut_bot_alert(
        symbol=symbol.upper(),
        timeframe=timeframe,
        ut_result=test_result,
        user_id=1,
        rule_cfg=cfg,
    )


@router.post("/notifications/test-msnr", response_model=Optional[NotificationRead])
async def test_msnr_dispatch(
    symbol: str = "XAUUSD",
    timeframe: str = "15m",
    direction: str = "BULLISH",
    db: AsyncSession = Depends(get_db),
):
    """
    Triggers an immediate test MSNR Key Level setup push notification to all registered FCM devices.
    Includes 50% Consequent Encroachment (CE), Classic V zone, and SMT Divergence.
    """
    service = NotificationService(db)
    test_setup = {
        "direction": direction.upper(),
        "setup_type": "DAILY_PROFILE_2_NY_REVERSAL",
        "entry_price": 4106.21,
        "stop_loss": 4098.50,
        "target_1": 4125.00,
        "target_2": 4180.00,
        "risk_reward": 9.5,
        "session_phase": "DISTRIBUTION_NY_AM",
        "smt_confluence": {"divergence_type": "BULLISH_SMT", "correlated_symbol": "XAGUSD"},
        "summary": "MSNR Classic V Support swept into 50% CE equilibrium @ 4106.21. Bullish SMT Divergence confirmed with XAGUSD Silver.",
    }
    cfg = NotificationService.DEFAULT_CONFIG.model_copy()
    cfg.cooldown_minutes = 0
    return await service.dispatch_msnr_setup_alert(
        symbol=symbol.upper(),
        setup=test_setup,
        timeframe=timeframe,
        user_id=1,
        rule_cfg=cfg,
    )


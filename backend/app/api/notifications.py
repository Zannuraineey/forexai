from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.notifications import NotificationService
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

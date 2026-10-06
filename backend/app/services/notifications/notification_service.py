import glob
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
import firebase_admin
from firebase_admin import credentials, messaging

from app.models.analysis import Notification, Device, AnalysisResult, AnalysisStateEnum
from app.models.instrument import Instrument
from app.schemas.ai_analysis import AnalysisRecordRead
from app.schemas.notification import (
    DeviceRegistrationRequest,
    DeviceRead,
    NotificationRuleConfig,
    NotificationRead,
)

logger = logging.getLogger("forex_ai.notifications")

def _get_firebase_app():
    """Lazily initializes and caches Firebase Admin app with service account credentials."""
    if firebase_admin._apps:
        return firebase_admin.get_app()
    candidates = (
        glob.glob("hope-*-firebase-adminsdk-*.json")
        + glob.glob("*-firebase-adminsdk-*.json")
        + ["firebase-service-account.json"]
    )
    for path in candidates:
        if os.path.exists(path):
            try:
                cred = credentials.Certificate(path)
                app = firebase_admin.initialize_app(cred)
                logger.info(f"Initialized Firebase Admin SDK with {path}")
                return app
            except Exception as e:
                logger.warning(f"Failed to initialize Firebase with {path}: {e}")
    return None

class NotificationService:
    """
    Decoupled Notification Layer.
    Adheres strictly to requirement:
    The notification engine must be separate from the AI engine.
    The AI produces an analysis result; a separate rules layer decides
    whether that result should trigger an FCM push notification.
    """

    # In-memory default rule configuration per user (can be extended to DB)
    DEFAULT_CONFIG = NotificationRuleConfig(
        notify_on_valid_setup=True,
        notify_on_potential_setup=False,
        notify_on_watch=False,
        notify_on_invalidation=False,
        cooldown_minutes=15,
        symbols_whitelist=[],
    )

    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_device(self, req: DeviceRegistrationRequest) -> DeviceRead:
        """
        Registers or updates an FCM push token for a mobile client.
        """
        stmt = select(Device).where(Device.fcm_token == req.fcm_token)
        res = await self.db.execute(stmt)
        device = res.scalar_one_or_none()

        now = datetime.now(timezone.utc)
        if device:
            device.user_id = req.user_id
            device.device_platform = req.device_platform
            device.last_active = now
        else:
            device = Device(
                user_id=req.user_id,
                fcm_token=req.fcm_token,
                device_platform=req.device_platform,
                last_active=now,
                created_at=now,
            )
            self.db.add(device)

        await self.db.commit()
        await self.db.refresh(device)
        return DeviceRead.model_validate(device)

    async def evaluate_and_dispatch(
        self,
        analysis: AnalysisRecordRead,
        user_id: int = 1,
        config: Optional[NotificationRuleConfig] = None,
    ) -> Optional[NotificationRead]:
        """
        Evaluates whether an AI analysis result satisfies user dispatch rules,
        checks deduplication/cooldown, and pushes to registered devices.
        """
        rule_cfg = config or self.DEFAULT_CONFIG

        # 1. Check State Eligibility
        state_str = analysis.state.value if hasattr(analysis.state, "value") else str(analysis.state)
        eligible = False
        if state_str == AnalysisStateEnum.VALID_SETUP.value and rule_cfg.notify_on_valid_setup:
            eligible = True
        elif state_str == AnalysisStateEnum.POTENTIAL_SETUP.value and rule_cfg.notify_on_potential_setup:
            eligible = True
        elif state_str == AnalysisStateEnum.WATCH.value and rule_cfg.notify_on_watch:
            eligible = True
        elif state_str == AnalysisStateEnum.INVALIDATED.value and rule_cfg.notify_on_invalidation:
            eligible = True

        if not eligible:
            logger.debug(f"Analysis {analysis.id} with state '{state_str}' not eligible for notification under current rules.")
            return None

        # 2. Check Whitelist
        if rule_cfg.symbols_whitelist and analysis.symbol.upper() not in [s.upper() for s in rule_cfg.symbols_whitelist]:
            logger.debug(f"Symbol '{analysis.symbol}' not in notification whitelist.")
            return None

        # 3. Check Deduplication & Cooldown
        cooldown_threshold = datetime.now(timezone.utc) - timedelta(minutes=rule_cfg.cooldown_minutes)
        dedup_stmt = (
            select(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.created_at >= cooldown_threshold,
            )
            .order_by(desc(Notification.created_at))
        )
        recent_res = await self.db.execute(dedup_stmt)
        recent_notifications = recent_res.scalars().all()

        for notif in recent_notifications:
            p = notif.payload or {}
            if (
                p.get("symbol") == analysis.symbol
                and p.get("timeframe") == analysis.timeframe
                and p.get("state") == state_str
            ):
                logger.info(f"Notification suppressed due to {rule_cfg.cooldown_minutes}m deduplication cooldown for {analysis.symbol}.")
                return None

        # 4. Fetch Devices
        dev_stmt = select(Device).where(Device.user_id == user_id)
        dev_res = await self.db.execute(dev_stmt)
        devices = dev_res.scalars().all()

        # Format Notification Content
        if state_str == AnalysisStateEnum.VALID_SETUP.value:
            title = f"🎯 VALID SETUP: {analysis.symbol} ({analysis.timeframe})"
        elif state_str == AnalysisStateEnum.POTENTIAL_SETUP.value:
            title = f"⚠️ SETUP FORMING: {analysis.symbol} ({analysis.timeframe})"
        else:
            title = f"AI Market Alert: {analysis.symbol} ({analysis.timeframe}) - {state_str}"

        body = analysis.summary

        payload = {
            "analysis_id": analysis.id,
            "symbol": analysis.symbol,
            "timeframe": analysis.timeframe,
            "state": state_str,
            "session": analysis.session_name,
            "timestamp_utc": analysis.timestamp_utc.isoformat(),
        }

        # 5. Dispatch to FCM via Firebase Admin SDK
        fb_app = _get_firebase_app()
        sent_count = 0
        if fb_app and devices:
            android_config = messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    sound="default",
                    priority="max",
                    default_vibrate_timings=True,
                    channel_id="forex_ai_alerts",
                    icon="ic_stat_notification",
                    color="#10B981",
                ),
            )
            for dev in devices:
                try:
                    msg = messaging.Message(
                        notification=messaging.Notification(
                            title=title,
                            body=body,
                        ),
                        data={k: str(v) for k, v in payload.items()},
                        android=android_config,
                        token=dev.fcm_token,
                    )
                    messaging.send(msg)
                    sent_count += 1
                    logger.info(f"FCM high-priority push delivered to device token {dev.fcm_token[:12]}...")
                except Exception as e:
                    logger.warning(f"Failed to deliver FCM push to device {dev.id}: {e}")

        status_val = "SENT" if (devices and sent_count > 0) else ("SENT_SIMULATED" if devices else "PENDING_NO_DEVICES")
        now = datetime.now(timezone.utc)

        notification_record = Notification(
            analysis_id=analysis.id,
            user_id=user_id,
            channel="fcm",
            title=title,
            body=body,
            payload=payload,
            sent_at=now if devices else None,
            status=status_val,
            created_at=now,
        )
        self.db.add(notification_record)
        await self.db.commit()
        await self.db.refresh(notification_record)

        logger.info(f"Dispatched notification {notification_record.id} for analysis {analysis.id} to {len(devices)} device(s) ({sent_count} live FCM delivered).")
        return NotificationRead.model_validate(notification_record)

    async def get_notifications(
        self, user_id: int = 1, limit: int = 50, offset: int = 0
    ) -> List[NotificationRead]:
        stmt = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(desc(Notification.created_at))
            .offset(offset)
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        records = res.scalars().all()
        return [NotificationRead.model_validate(r) for r in records]

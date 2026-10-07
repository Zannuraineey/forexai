import glob
import json
import base64
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
    """Lazily initializes and caches Firebase Admin app with service account credentials from env or files."""
    if firebase_admin._apps:
        return firebase_admin.get_app()

    # 1. Environment variable: raw JSON string
    env_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
    if env_json and env_json.strip():
        try:
            cert_dict = json.loads(env_json)
            cred = credentials.Certificate(cert_dict)
            app = firebase_admin.initialize_app(cred)
            logger.info("Initialized Firebase Admin SDK from FIREBASE_SERVICE_ACCOUNT_JSON environment variable")
            return app
        except Exception as e:
            logger.warning(f"Failed to initialize Firebase from FIREBASE_SERVICE_ACCOUNT_JSON: {e}")

    # 2. Environment variable: base64 encoded JSON (ideal for Railway/Docker without newline issues)
    env_b64 = os.environ.get("FIREBASE_SERVICE_ACCOUNT_BASE64")
    if env_b64 and env_b64.strip():
        try:
            raw_json = base64.b64decode(env_b64).decode("utf-8")
            cert_dict = json.loads(raw_json)
            cred = credentials.Certificate(cert_dict)
            app = firebase_admin.initialize_app(cred)
            logger.info("Initialized Firebase Admin SDK from FIREBASE_SERVICE_ACCOUNT_BASE64 environment variable")
            return app
        except Exception as e:
            logger.warning(f"Failed to initialize Firebase from FIREBASE_SERVICE_ACCOUNT_BASE64: {e}")

    # 3. Environment variable: file path
    env_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH")
    if env_path and os.path.exists(env_path):
        try:
            cred = credentials.Certificate(env_path)
            app = firebase_admin.initialize_app(cred)
            logger.info(f"Initialized Firebase Admin SDK from FIREBASE_SERVICE_ACCOUNT_PATH: {env_path}")
            return app
        except Exception as e:
            logger.warning(f"Failed to initialize Firebase from FIREBASE_SERVICE_ACCOUNT_PATH: {e}")

    # 4. Local files
    candidates = (
        glob.glob("hope-*-firebase-adminsdk-*.json")
        + glob.glob("*-firebase-adminsdk-*.json")
        + glob.glob("app/*-firebase-adminsdk-*.json")
        + ["firebase-service-account.json", "app/firebase-service-account.json"]
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

    logger.warning("No Firebase Admin credentials found! (FCM notifications will run in simulated mode until FIREBASE_SERVICE_ACCOUNT_BASE64 or FIREBASE_SERVICE_ACCOUNT_JSON is set)")
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
        notify_on_ut_bot=True,
        ut_bot_pairs=["R_75"],
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

    async def dispatch_ut_bot_alert(
        self,
        symbol: str,
        timeframe: str,
        ut_result: dict,
        user_id: int = 1,
        rule_cfg: Optional[NotificationRuleConfig] = None,
    ) -> Optional[NotificationRead]:
        """
        Dispatches a dedicated FCM push notification for UT Bot signals (BUY/SELL)
        specifically filtered for user-selected pairs.
        """
        cfg = rule_cfg or self.DEFAULT_CONFIG
        if not cfg.notify_on_ut_bot:
            return None

        sym = symbol.upper()
        # Verify symbol is in user's selected UT Bot pairs
        if cfg.ut_bot_pairs and sym not in [p.upper() for p in cfg.ut_bot_pairs]:
            logger.debug(f"UT Bot alert skipped: {sym} not in user selected ut_bot_pairs {cfg.ut_bot_pairs}.")
            return None

        signal = ut_result.get("signal", "WAIT")
        if signal not in ["BUY", "SELL"]:
            return None

        # Check deduplication & cooldown
        cooldown_threshold = datetime.now(timezone.utc) - timedelta(minutes=cfg.cooldown_minutes)
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
                p.get("strategy") == "ut_bot"
                and p.get("symbol") == sym
                and p.get("timeframe") == timeframe
                and p.get("signal") == signal
            ):
                logger.info(f"UT Bot notification suppressed due to {cfg.cooldown_minutes}m cooldown for {sym}.")
                return None

        # Fetch Devices
        dev_stmt = select(Device).where(Device.user_id == user_id)
        dev_res = await self.db.execute(dev_stmt)
        devices = dev_res.scalars().all()

        price = ut_result.get("current_price", 0.0)
        trail = ut_result.get("trailing_stop", 0.0)
        ema = ut_result.get("ema_200", 0.0)
        rsi = ut_result.get("rsi", 50.0)
        valid_str = ut_result.get("validity_window_str", "3 Minutes")
        rule_str = ut_result.get("execution_rule", "")
        tp1 = ut_result.get("take_profit_1", 0.0)
        tp2 = ut_result.get("take_profit_2", 0.0)
        max_slip = ut_result.get("max_slippage_points", 0.0)
        market_reg = ut_result.get("market_regime", "CONTINUOUS_24_7_SYNTHETIC")

        is_24_7 = "SYNTHETIC" in market_reg or "CRYPTO" in market_reg
        prefix = "⚡ [24/7 INSTANT]" if is_24_7 else "⚡ [UT BOT]"

        if signal == "BUY":
            title = f"{prefix} BUY: {sym} ({timeframe})"
            body = f"Entry: {price:.4f} | SL: {trail:.4f} | TP1: {tp1:.4f} | Valid: Next {valid_str}. Tap to execute."
        else:
            title = f"{prefix} SELL: {sym} ({timeframe})"
            body = f"Entry: {price:.4f} | SL: {trail:.4f} | TP1: {tp1:.4f} | Valid: Next {valid_str}. Tap to execute."

        payload = {
            "strategy": "ut_bot",
            "symbol": sym,
            "timeframe": timeframe,
            "signal": signal,
            "price": str(price),
            "trailing_stop": str(trail),
            "take_profit_1": str(tp1),
            "take_profit_2": str(tp2),
            "max_slippage_points": str(max_slip),
            "execution_rule": rule_str,
            "validity_window_str": valid_str,
            "market_regime": market_reg,
            "ema_200": str(ema),
            "rsi": str(rsi),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }

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
                    color="#10B981" if signal == "BUY" else "#EF4444",
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
                    logger.info(f"FCM UT Bot push delivered to {sym} on device token {dev.fcm_token[:12]}...")
                except Exception as e:
                    logger.warning(f"Failed to deliver FCM UT Bot push: {e}")

        status_val = "SENT" if (devices and sent_count > 0) else ("SENT_SIMULATED" if devices else "PENDING_NO_DEVICES")
        now = datetime.now(timezone.utc)
        record = Notification(
            analysis_id=None,
            user_id=user_id,
            channel="fcm",
            title=title,
            body=body,
            payload=payload,
            sent_at=now if devices else None,
            status=status_val,
            created_at=now,
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        logger.info(f"Dispatched UT Bot notification {record.id} for {sym} ({sent_count} live FCM delivered).")
        return NotificationRead.model_validate(record)

    async def dispatch_economic_event_alert(
        self,
        event: Any,  # EconomicEvent
        minutes_until: int,
        user_id: int = 1,
    ) -> Optional[NotificationRead]:
        """
        Dispatches high-priority pre-release FCM notification (5-10 minutes prior to release)
        for high and medium impact economic events.
        """
        # Deduplication: check if this event was already alerted
        cooldown_threshold = datetime.now(timezone.utc) - timedelta(hours=3)
        dedup_stmt = (
            select(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.created_at >= cooldown_threshold,
            )
            .order_by(desc(Notification.created_at))
        )
        recent_res = await self.db.execute(dedup_stmt)
        for notif in recent_res.scalars().all():
            p = notif.payload or {}
            if p.get("type") == "ECONOMIC_EVENT_UPCOMING" and str(p.get("event_id")) == str(event.id):
                logger.info(f"Economic event notification suppressed: {event.id} already alerted.")
                return None

        # Fetch registered devices
        dev_stmt = select(Device).where(Device.user_id == user_id)
        dev_res = await self.db.execute(dev_stmt)
        devices = dev_res.scalars().all()

        impact_icon = "🚨" if getattr(event, "impact", "") == "HIGH" else "⚡"
        title = f"{impact_icon} [{getattr(event, 'impact', 'HIGH')}] {getattr(event, 'currency', 'USD')}: {getattr(event, 'title', 'Economic Event')} in {minutes_until}m"

        fc_str = getattr(event, "raw_forecast", None) or (f"{getattr(event, 'forecast', '')}{getattr(event, 'unit', '')}" if getattr(event, "forecast", None) is not None else "N/A")
        prev_str = getattr(event, "raw_previous", None) or (f"{getattr(event, 'previous', '')}{getattr(event, 'unit', '')}" if getattr(event, "previous", None) is not None else "N/A")

        bull_trig = getattr(event, "bullish_trigger", None)
        consensus = getattr(event, "consensus_expectation", None)
        if bull_trig:
            body = f"Forecast: {fc_str} vs Prior: {prev_str}. {bull_trig}"
        elif consensus:
            body = f"Forecast: {fc_str} vs Prior: {prev_str}. {consensus}"
        else:
            body = f"High volatility event approaching in {minutes_until} minutes. Prepare dealing range setups."

        payload = {
            "type": "ECONOMIC_EVENT_UPCOMING",
            "screen": "news",
            "event_id": str(getattr(event, "id", "")),
            "currency": str(getattr(event, "currency", "USD")),
            "impact": str(getattr(event, "impact", "HIGH")),
            "title": str(getattr(event, "title", "")),
            "minutes_until": str(minutes_until),
            "forecast": str(fc_str),
            "previous": str(prev_str),
            "bullish_trigger": str(getattr(event, "bullish_trigger", "") or ""),
            "bearish_trigger": str(getattr(event, "bearish_trigger", "") or ""),
            "click_action": "FLUTTER_NOTIFICATION_CLICK",
        }

        sent_count = 0
        fb_app = _get_firebase_app()
        if fb_app and devices:
            android_config = messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    sound="default",
                    priority="max",
                    default_vibrate_timings=True,
                    channel_id="forex_ai_alerts",
                    icon="ic_stat_notification",
                    color="#EF4444" if getattr(event, "impact", "") == "HIGH" else "#F59E0B",
                ),
            )
            for dev in devices:
                try:
                    msg = messaging.Message(
                        notification=messaging.Notification(title=title, body=body),
                        data={k: str(v) for k, v in payload.items()},
                        android=android_config,
                        token=dev.fcm_token,
                    )
                    messaging.send(msg)
                    sent_count += 1
                    logger.info(f"FCM economic event push delivered for {getattr(event, 'title', '')} to {dev.fcm_token[:12]}...")
                except Exception as e:
                    logger.warning(f"Failed to deliver FCM economic event push to device {dev.id}: {e}")

            # Also broadcast to topic "economic_events"
            try:
                topic_msg = messaging.Message(
                    notification=messaging.Notification(title=title, body=body),
                    data={k: str(v) for k, v in payload.items()},
                    android=android_config,
                    topic="economic_events",
                )
                messaging.send(topic_msg)
                logger.info("Delivered FCM event broadcast to topic 'economic_events'")
            except Exception as e:
                logger.debug(f"Topic broadcast notice: {e}")

        now = datetime.now(timezone.utc)
        record = Notification(
            analysis_id=None,
            user_id=user_id,
            channel="fcm",
            title=title,
            body=body,
            payload=payload,
            sent_at=now if (devices and sent_count > 0) else None,
            status="SENT" if (devices and sent_count > 0) else ("SENT_SIMULATED" if devices else "PENDING_NO_DEVICES"),
            created_at=now,
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        logger.info(f"Dispatched economic event pre-release notification {record.id} for {getattr(event, 'title', '')}.")
        return NotificationRead.model_validate(record)

    async def dispatch_daily_events_briefing(
        self,
        events: List[Any],  # List[EconomicEvent]
        user_id: int = 1,
    ) -> Optional[NotificationRead]:
        """
        Dispatches daily morning economic schedule briefing to user mobile devices.
        """
        if not events:
            return None

        # Check deduplication for today
        now = datetime.now(timezone.utc)
        start_of_day = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        dedup_stmt = (
            select(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.created_at >= start_of_day,
            )
        )
        recent_res = await self.db.execute(dedup_stmt)
        for notif in recent_res.scalars().all():
            p = notif.payload or {}
            if p.get("type") == "ECONOMIC_EVENT_DAILY_BRIEFING":
                logger.info("Daily economic briefing already sent today.")
                return None

        # Fetch registered devices
        dev_stmt = select(Device).where(Device.user_id == user_id)
        dev_res = await self.db.execute(dev_stmt)
        devices = dev_res.scalars().all()

        high_count = sum(1 for e in events if getattr(e, "impact", "") == "HIGH")
        title = f"📅 Today's Macro Events Radar ({len(events)} Releases, {high_count} High Impact)"

        # Format top 3 key events
        event_snippets = []
        for e in events[:3]:
            dt = getattr(e, "event_time_utc", None)
            time_str = dt.strftime("%H:%M UTC") if dt else ""
            event_snippets.append(f"{getattr(e, 'currency', 'USD')} {getattr(e, 'title', '')} ({time_str})")
        body = "Key today: " + "; ".join(event_snippets) + ". Review scenario triggers before market open."

        payload = {
            "type": "ECONOMIC_EVENT_DAILY_BRIEFING",
            "screen": "news",
            "event_count": str(len(events)),
            "high_count": str(high_count),
            "click_action": "FLUTTER_NOTIFICATION_CLICK",
        }

        sent_count = 0
        fb_app = _get_firebase_app()
        if fb_app and devices:
            android_config = messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    sound="default",
                    priority="max",
                    default_vibrate_timings=True,
                    channel_id="forex_ai_alerts",
                    icon="ic_stat_notification",
                    color="#3B82F6",
                ),
            )
            for dev in devices:
                try:
                    msg = messaging.Message(
                        notification=messaging.Notification(title=title, body=body),
                        data={k: str(v) for k, v in payload.items()},
                        android=android_config,
                        token=dev.fcm_token,
                    )
                    messaging.send(msg)
                    sent_count += 1
                except Exception as e:
                    logger.warning(f"Failed to deliver FCM daily briefing: {e}")

            try:
                topic_msg = messaging.Message(
                    notification=messaging.Notification(title=title, body=body),
                    data={k: str(v) for k, v in payload.items()},
                    android=android_config,
                    topic="economic_events",
                )
                messaging.send(topic_msg)
            except Exception as e:
                logger.debug(f"Topic broadcast notice: {e}")

        now = datetime.now(timezone.utc)
        record = Notification(
            analysis_id=None,
            user_id=user_id,
            channel="fcm",
            title=title,
            body=body,
            payload=payload,
            sent_at=now if (devices and sent_count > 0) else None,
            status="SENT" if (devices and sent_count > 0) else ("SENT_SIMULATED" if devices else "PENDING_NO_DEVICES"),
            created_at=now,
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        logger.info(f"Dispatched daily economic briefing notification {record.id}.")
        return NotificationRead.model_validate(record)

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

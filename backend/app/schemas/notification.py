from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, ConfigDict, Field

class DeviceRegistrationRequest(BaseModel):
    fcm_token: str = Field(..., description="Unique FCM registration token from mobile client")
    device_platform: str = Field(..., description="'android' or 'ios'")
    user_id: int = 1

class DeviceRead(BaseModel):
    id: int
    user_id: int
    fcm_token: str
    device_platform: str
    last_active: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class NotificationRuleConfig(BaseModel):
    notify_on_valid_setup: bool = True
    notify_on_potential_setup: bool = False
    notify_on_watch: bool = False
    notify_on_invalidation: bool = False
    notify_on_ut_bot: bool = True
    ut_bot_pairs: List[str] = ["R_75"]
    cooldown_minutes: int = 15
    symbols_whitelist: List[str] = []

class NotificationRead(BaseModel):
    id: int
    analysis_id: Optional[int] = None
    user_id: int
    channel: str
    title: str
    body: str
    payload: Dict[str, Any]
    status: str
    sent_at: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict

class TargetClassification(str, Enum):
    NORMAL_TARGET = "NORMAL_TARGET"
    EXTENDED_TARGET = "EXTENDED_TARGET"
    EXTREME_TARGET = "EXTREME_TARGET"
    TARGET_BEYOND_AVAILABLE_CONTEXT = "TARGET_BEYOND_AVAILABLE_CONTEXT"

class TargetRealismMetrics(BaseModel):
    """
    Comprehensive quantitative metrics evaluating whether a Take Profit target
    is standard, extended, or an extreme statistical outlier.
    """
    risk_distance: float
    reward_distance: float
    rr_ratio: float
    target_distance_pips: float
    target_distance_atr: Optional[float] = None
    target_distance_percent: float
    distance_to_nearest_liquidity: Optional[float] = None
    distance_to_previous_high: Optional[float] = None
    distance_to_previous_low: Optional[float] = None
    distance_to_session_high: Optional[float] = None
    distance_to_session_low: Optional[float] = None
    distance_to_daily_high: Optional[float] = None
    distance_to_daily_low: Optional[float] = None
    classification: TargetClassification
    classification_reason: str
    policy_applied: str = "STRUCTURAL_ALLOW_WITH_TAGGING"
    statistical_support_status: str = "INSUFFICIENT_DATA"
    historical_sample_size: Optional[int] = None
    historical_hit_rate: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)

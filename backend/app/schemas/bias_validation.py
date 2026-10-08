from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class FinalBiasState(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    CONFLICTED = "CONFLICTED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class BiasQuality(str, Enum):
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"
    UNUSABLE = "UNUSABLE"


class SevenHourRelationship(str, Enum):
    SUPPORT = "SUPPORT"
    CONTRADICT = "CONTRADICT"
    NEUTRAL = "NEUTRAL"
    UNAVAILABLE = "UNAVAILABLE"


class DXYRelationship(str, Enum):
    SUPPORTIVE = "SUPPORTIVE"
    CONTRADICTING = "CONTRADICTING"
    NEUTRAL = "NEUTRAL"
    UNAVAILABLE = "UNAVAILABLE"


class NewsRiskLevel(str, Enum):
    LOW_RISK = "LOW_RISK"
    MEDIUM_RISK = "MEDIUM_RISK"
    HIGH_RISK = "HIGH_RISK"
    EVENT_IMMINENT = "EVENT_IMMINENT"
    EVENT_ACTIVE = "EVENT_ACTIVE"
    POST_EVENT = "POST_EVENT"
    UNAVAILABLE = "UNAVAILABLE"


class BiasValidationResult(BaseModel):
    """
    Structured output of the Unified Multi-Layer Bias Validation Engine.
    Combines independent multi-timeframe structure, 7H Profile, session timing,
    liquidity events, DXY intermarket flow, and macro news into an objective
    directional assessment without arbitrary probability numbers.
    """
    symbol: str
    timestamp: str
    final_bias: FinalBiasState
    bias_quality: BiasQuality
    htf_bias: Dict[str, Any]
    seven_hour_bias: Dict[str, Any] = Field(default_factory=dict)
    mtf_alignment: Dict[str, Any] = Field(default_factory=dict)
    structure_state: Dict[str, Any] = Field(default_factory=dict)
    liquidity_event: Dict[str, Any] = Field(default_factory=dict)
    mss_state: Dict[str, Any] = Field(default_factory=dict)
    session_context: Dict[str, Any] = Field(default_factory=dict)
    dxy_context: Dict[str, Any] = Field(default_factory=dict)
    news_context: Dict[str, Any] = Field(default_factory=dict)
    conflicts: List[str] = Field(default_factory=list)
    missing_data: List[str] = Field(default_factory=list)
    explanation: str
    validation_status: str

    @property
    def seven_hour_context(self) -> Dict[str, Any]:
        return self.seven_hour_bias

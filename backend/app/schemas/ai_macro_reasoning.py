from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict

class MacroBiasState(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    MIXED = "MIXED"
    UNAVAILABLE = "UNAVAILABLE"

class MacroRiskLevel(str, Enum):
    LOW_RISK = "LOW_RISK"
    MEDIUM_RISK = "MEDIUM_RISK"
    HIGH_RISK = "HIGH_RISK"
    EVENT_IMMINENT = "EVENT_IMMINENT"
    EVENT_ACTIVE = "EVENT_ACTIVE"
    POST_EVENT = "POST_EVENT"
    UNAVAILABLE = "UNAVAILABLE"

class SupportedModelInfo(BaseModel):
    id: str
    name: str
    description: str
    context_window: int = 8192
    is_default: bool = False

class SupportedProviderInfo(BaseModel):
    id: str
    name: str
    description: str
    default_model: str
    supports_custom_base_url: bool = False
    default_base_url: Optional[str] = None
    models: List[SupportedModelInfo] = []

class AIMacroConfigRequest(BaseModel):
    provider: str = Field(..., description="Provider ID (groq, xai, gemini, openai, deepseek)")
    model: str = Field(..., description="Model ID")
    is_enabled: bool = Field(default=True)
    api_key: Optional[str] = Field(None, description="New API key (optional; if empty, retains existing stored key)")
    api_base_url: Optional[str] = Field(None, description="Optional custom base URL for OpenAI-compatible proxies")

class AIMacroConfigSafeRead(BaseModel):
    """
    Client-facing safe configuration.
    CRITICAL: Never exposes plaintext API key to client or logs.
    """
    user_id: str
    provider: str
    model: str
    is_enabled: bool
    has_api_key: bool
    masked_key: Optional[str] = None
    api_base_url: Optional[str] = None
    last_tested_at: Optional[datetime] = None
    last_test_status: Optional[str] = None
    last_test_latency_ms: Optional[int] = None
    last_test_error: Optional[str] = None
    updated_at_utc: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class AIMacroTestRequest(BaseModel):
    provider: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = Field(None, description="Optional temporary key to test before saving")
    api_base_url: Optional[str] = None

class AIMacroTestResponse(BaseModel):
    status: str  # "SUCCESS", "FAILED"
    provider: str
    model: str
    latency_ms: int
    message: str
    error: Optional[str] = None
    tested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AIMacroReasoningOutput(BaseModel):
    """
    Validated, institutional response structure returned by Macro Reasoning Engine.
    """
    summary: str
    relevant_events: List[Dict[str, Any]] = []
    usd_macro_bias: MacroBiasState
    dxy_context: str
    instrument_implications: Dict[str, str] = {}
    supporting_evidence: List[str] = []
    contradicting_evidence: List[str] = []
    risk_level: MacroRiskLevel
    data_gaps: List[str] = []
    generated_at: datetime
    provider: str
    model: str
    status: str = "SUCCESS"  # "SUCCESS", "UNAVAILABLE", "ERROR", "FALLBACK_QUANT"
    cached: bool = False
    token_usage: Optional[Dict[str, int]] = None

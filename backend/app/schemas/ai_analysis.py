from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, ConfigDict, Field
from app.models.analysis import AnalysisStateEnum

from app.schemas.target_realism import TargetRealismMetrics
from app.schemas.setup_snapshot import SetupContextSnapshot
from app.schemas.bias_validation import BiasValidationResult

class ConditionStatus(BaseModel):
    condition: str
    satisfied: bool
    evidence: str
    notes: Optional[str] = None

class AmbiguityItem(BaseModel):
    text_snippet: str
    reason: str
    suggestion: Optional[str] = None

class TradeTarget(BaseModel):
    price: float
    rr: float
    action: str

    model_config = ConfigDict(from_attributes=True)

class InvalidationRule(BaseModel):
    expiry_minutes: int = 30
    cancel_if_touched: Optional[float] = None
    note: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class TradeSetup(BaseModel):
    action: str  # "BUY LIMIT" or "SELL LIMIT"
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_pips: float
    targets: Dict[str, TradeTarget] = Field(default_factory=dict)
    invalidation: InvalidationRule = Field(default_factory=InvalidationRule)
    confluence: List[str] = Field(default_factory=list)
    grade: Optional[str] = "Grade A"
    session: Optional[str] = None
    model: Optional[str] = None
    rr_ratio: Optional[float] = None
    sl_buffer_pips: Optional[float] = None
    target_realism: Optional[TargetRealismMetrics] = None
    setup_snapshot: Optional[SetupContextSnapshot] = None
    bias_validation: Optional[BiasValidationResult] = None

    model_config = ConfigDict(from_attributes=True)

class AIAnalysisOutput(BaseModel):
    state: AnalysisStateEnum = AnalysisStateEnum.NO_SETUP
    summary: str
    condition_breakdown: List[ConditionStatus] = []
    ambiguities_detected: List[AmbiguityItem] = []
    confidence_notes: Optional[str] = None
    full_reasoning: Optional[str] = None
    trade_setup: Optional[TradeSetup] = None
    setup_snapshot: Optional[SetupContextSnapshot] = None
    bias_validation: Optional[BiasValidationResult] = None

    model_config = ConfigDict(from_attributes=True)

class AIAnalysisRequest(BaseModel):
    symbol: str
    timeframe: str = "15m"
    session_name: Optional[str] = None
    instruction_version_id: Optional[int] = None
    custom_instructions: Optional[str] = None

class AnalysisRecordRead(BaseModel):
    id: int
    symbol: str
    instrument_id: int
    candle_id: Optional[int] = None
    timeframe: str
    timestamp_utc: datetime
    session_name: str
    instruction_version_id: Optional[int] = None
    instruction_version_number: Optional[int] = None
    model_version: str
    state: AnalysisStateEnum
    summary: str
    condition_breakdown: List[ConditionStatus] = []
    ambiguities_detected: List[AmbiguityItem] = []
    full_reasoning: Optional[str] = None
    trade_setup: Optional[TradeSetup] = None
    setup_snapshot: Optional[SetupContextSnapshot] = None
    bias_validation: Optional[BiasValidationResult] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AnalysisQueryFilter(BaseModel):
    symbol: Optional[str] = None
    timeframe: Optional[str] = None
    session_name: Optional[str] = None
    state: Optional[AnalysisStateEnum] = None
    limit: int = 50
    offset: int = 0


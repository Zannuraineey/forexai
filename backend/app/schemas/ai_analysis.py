from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, ConfigDict, Field
from app.models.analysis import AnalysisStateEnum

class ConditionStatus(BaseModel):
    condition: str
    satisfied: bool
    evidence: str
    notes: Optional[str] = None

class AmbiguityItem(BaseModel):
    text_snippet: str
    reason: str
    suggestion: Optional[str] = None

class AIAnalysisOutput(BaseModel):
    state: AnalysisStateEnum = AnalysisStateEnum.NO_SETUP
    summary: str
    condition_breakdown: List[ConditionStatus] = []
    ambiguities_detected: List[AmbiguityItem] = []
    confidence_notes: Optional[str] = None
    full_reasoning: Optional[str] = None

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
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AnalysisQueryFilter(BaseModel):
    symbol: Optional[str] = None
    timeframe: Optional[str] = None
    session_name: Optional[str] = None
    state: Optional[AnalysisStateEnum] = None
    limit: int = 50
    offset: int = 0

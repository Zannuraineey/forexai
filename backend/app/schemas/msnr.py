from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
try:
    from app.schemas.smt import SMTDivergenceDetail  # type: ignore
except (ImportError, ModuleNotFoundError):
    from .smt import SMTDivergenceDetail  # type: ignore



class MSNRZoneType(str, Enum):
    CLASSIC_A = "CLASSIC_A"  # Peak / Resistance
    CLASSIC_V = "CLASSIC_V"  # Trough / Support
    RBS = "RBS"              # Resistance Becomes Support (Bullish Flip)
    SBR = "SBR"              # Support Becomes Resistance (Bearish Flip)


class MSNRZoneQuality(str, Enum):
    FRESH = "FRESH"          # 0-1 prior touches (Highest probability)
    TESTED = "TESTED"        # 2 touches
    EXHAUSTED = "EXHAUSTED"  # 3+ touches (Breakout imminent)


class MSNRZone(BaseModel):
    zone_type: MSNRZoneType
    top_price: float
    bottom_price: float
    level_price: float
    consequent_encroachment_50: float = Field(..., description="50% CE level of reaction candle/zone")
    touches_count: int = 0
    quality: MSNRZoneQuality = MSNRZoneQuality.FRESH
    formed_at_utc: datetime
    broken_at_utc: Optional[datetime] = None
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class MSNRSetupType(str, Enum):
    BULLISH_RBS_RETEST = "BULLISH_RBS_RETEST"
    BEARISH_SBR_RETEST = "BEARISH_SBR_RETEST"
    DAILY_PROFILE_2_NY_REVERSAL = "DAILY_PROFILE_2_NY_REVERSAL"
    LIQUIDITY_SWEEP_CE_RETEST = "LIQUIDITY_SWEEP_CE_RETEST"


class MSNRSetupSignal(BaseModel):
    symbol: str
    setup_type: MSNRSetupType
    direction: str  # "BULLISH" or "BEARISH"
    zone: MSNRZone
    entry_price: float = Field(..., description="50% CE level entry")
    stop_loss: float = Field(..., description="Invalidation beyond zone/wick extreme")
    target_1: float = Field(..., description="Interim target: Opposing session high/low or IRL")
    target_2: float = Field(..., description="Macro target: External Range Liquidity (ERL)")
    risk_reward: float
    session_phase: str = Field(..., description="Accumulation, Manipulation, Distribution (NY), or Continuation")
    smt_confluence: Optional[SMTDivergenceDetail] = None
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    summary: str

    model_config = ConfigDict(from_attributes=True)


class MSNRAnalysisResult(BaseModel):
    symbol: str
    timestamp_utc: datetime
    active_zones: List[MSNRZone] = []
    signals: List[MSNRSetupSignal] = []
    has_active_setup: bool = False
    highest_quality_signal: Optional[MSNRSetupSignal] = None

    model_config = ConfigDict(from_attributes=True)

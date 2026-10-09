from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict, Field

class SMTDivergenceType(str, Enum):
    NONE = "NONE"
    BULLISH_SMT = "BULLISH_SMT"  # Swept low on one pair, higher low on correlated pair
    BEARISH_SMT = "BEARISH_SMT"  # Swept high on one pair, lower high on correlated pair

class SMTPairGroup(str, Enum):
    METALS = "METALS"  # XAUUSD vs XAGUSD
    MAJORS = "MAJORS"  # EURUSD vs GBPUSD
    DOLLAR_INVERSE = "DOLLAR_INVERSE"  # EURUSD vs DXY (Inverse)

class SMTDivergenceDetail(BaseModel):
    """
    Structured representation of an SMT Divergence event between correlated instruments.
    """
    pair_group: SMTPairGroup = SMTPairGroup.METALS
    primary_symbol: str
    correlated_symbol: str
    divergence_type: SMTDivergenceType = SMTDivergenceType.NONE
    swept_symbol: Optional[str] = None  # The symbol that took liquidity (Lower Low or Higher High)
    strong_symbol: Optional[str] = None  # The symbol that held structure (Higher Low or Lower High)
    reference_level: str = "SESSION_SWEEP"  # ASIAN_LOW, LONDON_HIGH, 7H_EXTREME, FRACTAL_SWING
    primary_delta_pct: Optional[float] = None
    correlated_delta_pct: Optional[float] = None
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    summary: str
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)

class SMTContext(BaseModel):
    """
    Aggregated SMT divergence context for a target symbol.
    """
    symbol: str
    correlated_symbol: Optional[str] = None
    has_smt_divergence: bool = False
    active_divergence: Optional[SMTDivergenceDetail] = None
    all_correlations: List[SMTDivergenceDetail] = []
    confluence_bias: str = "NEUTRAL"  # "BULLISH", "BEARISH", "NEUTRAL"
    confidence_boost: float = 0.0

    model_config = ConfigDict(from_attributes=True)

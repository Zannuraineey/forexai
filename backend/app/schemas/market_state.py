from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict

from app.schemas.seven_hour_profile import (
    SevenHourProfileResult,
    ProfileClassification,
    ProfileDirection,
    ProfileStatus,
    DataQuality,
    ProfileRelationship,
)
from app.services.session.session_engine import CurrentSessionState, SessionLevels


class SevenHourProfileContext(BaseModel):
    """Structured representation of the current synthetic 7H profile."""
    classification: ProfileClassification = ProfileClassification.INSUFFICIENT_DATA
    direction: ProfileDirection = ProfileDirection.NEUTRAL
    range: float = 0.0
    normalized_range: Optional[float] = None
    previous_relationship: Optional[ProfileRelationship] = None
    status: ProfileStatus = ProfileStatus.IN_PROGRESS
    data_quality: DataQuality = DataQuality.INSUFFICIENT
    profile_start: Optional[datetime] = None
    profile_end: Optional[datetime] = None
    source_candle_count: int = 0
    config_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SessionContext(BaseModel):
    """Structured market session context (institutional timing, killzones, session levels)."""
    active_sessions: List[str] = []
    primary_session: Optional[str] = None
    overlap: bool = False
    overlap_name: Optional[str] = None
    killzone: Dict[str, Any] = {}
    session_levels: Dict[str, SessionLevels] = {}

    model_config = ConfigDict(from_attributes=True)


class TimeframeSummary(BaseModel):
    """Micro-summary of an individual timeframe."""
    timeframe: str
    candle_count: int = 0
    last_candle_timestamp: Optional[datetime] = None
    current_price: Optional[float] = None
    trend: str = "UNDEFINED"
    rsi_14: Optional[float] = None
    atr_14: Optional[float] = None
    ema_21: Optional[float] = None
    ema_50: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class TimeframeContext(BaseModel):
    """Multi-timeframe hierarchy covering HTF to LTF."""
    tf_4h: Optional[TimeframeSummary] = None
    tf_1h: Optional[TimeframeSummary] = None
    tf_15m: Optional[TimeframeSummary] = None
    requested_timeframe: str
    requested: Optional[TimeframeSummary] = None

    model_config = ConfigDict(from_attributes=True)


class StructureContext(BaseModel):
    """Pure price structure (trend state, shifts, swing points)."""
    trend: str = "UNDEFINED"  # "BULLISH", "BEARISH", "CONSOLIDATION", "UNDEFINED"
    recent_mss: List[Dict[str, Any]] = []
    recent_bos: List[Dict[str, Any]] = []
    swings: List[Dict[str, Any]] = []

    model_config = ConfigDict(from_attributes=True)


class LiquidityContext(BaseModel):
    """Liquidity references and confirmed sweeps."""
    bsl: Optional[float] = None  # Buy-Side Liquidity reference (e.g. PDH / Swing High)
    ssl: Optional[float] = None  # Sell-Side Liquidity reference (e.g. PDL / Swing Low)
    recent_sweeps: List[Dict[str, Any]] = []

    model_config = ConfigDict(from_attributes=True)


class ProfileSessionInteraction(BaseModel):
    """
    Factual cross-layer relationship between 7H Profile and Session Context.
    IMPORTANT: Contains NO trade signals or directional bias recommendations.
    """
    profile_direction: Optional[ProfileDirection] = None
    active_session: Optional[str] = None
    killzone_active: bool = False
    killzone_name: Optional[str] = None
    recent_session_event: Optional[str] = None  # e.g. "SSL_SWEEP", "BSL_SWEEP", "NONE"
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class HistoricalProfileContext(BaseModel):
    """
    Empirical historical profile performance statistics.
    Returns None / null where statistics are unavailable (never invents probabilities).
    """
    profile_sample_size: Optional[int] = None
    profile_win_rate: Optional[float] = None
    historical_mfe: Optional[float] = None
    historical_mae: Optional[float] = None
    historical_r_multiple_distribution: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class StructuredMarketState(BaseModel):
    """
    Unified, multi-layer market context assembly.
    Combines independent 7H Profile, Session Engine, Multi-timeframe,
    Structure, and Liquidity contexts without generating trade setups.
    """
    symbol: str
    timestamp_utc: datetime
    current_price: float
    seven_hour_profile: SevenHourProfileContext
    session: SessionContext
    timeframe_context: TimeframeContext
    structure: StructureContext
    liquidity: LiquidityContext
    profile_vs_session_interaction: ProfileSessionInteraction
    historical_profile_context: Optional[HistoricalProfileContext] = None

    model_config = ConfigDict(from_attributes=True)

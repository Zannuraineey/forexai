from datetime import datetime, time
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class ProfileStatus(str, Enum):
    COMPLETED = "COMPLETED"
    IN_PROGRESS = "IN_PROGRESS"

class ProfileDirection(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"

class ProfileClassification(str, Enum):
    BULLISH_EXPANSION = "BULLISH_EXPANSION"
    BEARISH_EXPANSION = "BEARISH_EXPANSION"
    BULLISH_CONTINUATION = "BULLISH_CONTINUATION"
    BEARISH_CONTINUATION = "BEARISH_CONTINUATION"
    BULLISH_REVERSAL = "BULLISH_REVERSAL"
    BEARISH_REVERSAL = "BEARISH_REVERSAL"
    RANGE_CONSOLIDATION = "RANGE_CONSOLIDATION"
    FAILED_BULLISH_EXPANSION = "FAILED_BULLISH_EXPANSION"
    FAILED_BEARISH_EXPANSION = "FAILED_BEARISH_EXPANSION"
    UNCLASSIFIED = "UNCLASSIFIED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

class DataQuality(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    INSUFFICIENT = "INSUFFICIENT"

class SevenHourProfileConfig(BaseModel):
    """
    Explicit, configurable anchor configuration for synthetic 7H candle boundaries.
    
    Assumption documentation:
    Since 7 hours does not divide 24 hours evenly (24 / 7 = 3.428...), a 7H series
    requires an explicit anchor timestamp and alignment mode.
    - anchor_timezone: IANA timezone (e.g. 'UTC', 'America/New_York')
    - anchor_start: Local time of day anchoring the sequence (default: 00:00)
    - duration_hours: Window length in hours (default: 7)
    - source_timeframe: Lower-timeframe source bars (default: '1h')
    - alignment_mode: 'CONTINUOUS' (continuous 7H blocks from anchor baseline) 
                      or 'DAILY_ANCHOR' (resets each day at anchor_start)
    """
    anchor_timezone: str = "UTC"
    anchor_start: time = time(0, 0)
    duration_hours: int = 7
    source_timeframe: str = "1h"
    number_of_completed_profiles_required: int = 2
    alignment_mode: str = "DAILY_ANCHOR" # "DAILY_ANCHOR" (resets at anchor_start) or "CONTINUOUS"
    config_id: str = "UTC_0000_7H"
    pip_size: float = 0.0001
    min_candles_ratio_for_complete: float = 1.0 # 100% of expected candles required for COMPLETE

    model_config = ConfigDict(from_attributes=True)

class ProfileRelationship(BaseModel):
    took_previous_high: bool = False
    took_previous_low: bool = False
    closed_above_previous_high: bool = False
    closed_below_previous_low: bool = False
    closed_inside_previous_range: bool = False
    open_inside_previous_range: bool = False
    current_range: float = 0.0
    previous_range: Optional[float] = None
    expansion_ratio: Optional[float] = None
    expanded_vs_previous: bool = False
    contracted_vs_previous: bool = False
    continuation: bool = False
    reversal: bool = False
    failed_expansion: bool = False
    close_location_relative_to_previous_range: Optional[float] = None
    previous_high: Optional[float] = None
    previous_low: Optional[float] = None
    previous_close: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)

class SevenHourQuantitativeFeatures(BaseModel):
    range: float
    normalized_range: Optional[float] = None # in pips or normalized units
    body: float
    upper_wick: float
    lower_wick: float
    body_ratio: float
    close_location: float
    range_vs_atr: Optional[float] = None
    expansion_ratio: Optional[float] = None
    previous_range: Optional[float] = None
    range_percentile: Optional[float] = None
    high_taken: bool = False
    low_taken: bool = False
    close_above_previous_high: bool = False
    close_below_previous_low: bool = False

    model_config = ConfigDict(from_attributes=True)

class PreviousProfileSummary(BaseModel):
    profile_start: datetime
    profile_end: datetime
    open: float
    high: float
    low: float
    close: float
    range: float
    body: float
    direction: ProfileDirection
    classification: ProfileClassification

    model_config = ConfigDict(from_attributes=True)

class SevenHourProfileResult(BaseModel):
    symbol: str
    profile_start: datetime
    profile_end: datetime
    status: ProfileStatus
    open: float
    high: float
    low: float
    close: float
    direction: ProfileDirection
    range: float
    body: float
    body_ratio: float
    close_location: float
    features: SevenHourQuantitativeFeatures
    previous_profile: Optional[PreviousProfileSummary] = None
    relationship: Optional[ProfileRelationship] = None
    classification: ProfileClassification
    source_timeframe: str
    source_candle_count: int
    expected_candle_count: int
    data_quality: DataQuality
    config_id: str

    model_config = ConfigDict(from_attributes=True)

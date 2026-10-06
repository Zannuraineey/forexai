from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict

class CandleDTO(BaseModel):
    """Data Transfer Object for candles ingested from providers."""
    symbol: str
    timeframe: str
    timestamp_utc: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    provider: str = "deriv"
    is_complete: bool = True

    model_config = ConfigDict(from_attributes=True)

class CandleRead(BaseModel):
    id: int
    instrument_id: int
    timeframe: str
    timestamp_utc: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    provider: str
    is_complete: bool

    model_config = ConfigDict(from_attributes=True)

class CandleBatchRead(BaseModel):
    symbol: str
    timeframe: str
    count: int
    candles: List[CandleRead]

class GapReport(BaseModel):
    symbol: str
    timeframe: str
    last_stored_timestamp: Optional[datetime]
    now_utc: datetime
    gap_duration_seconds: float
    missing_bars_estimated: int
    recovered_bars: int = 0
    status: str

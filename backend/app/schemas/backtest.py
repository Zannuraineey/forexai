from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, ConfigDict

class BacktestRequest(BaseModel):
    symbol: str
    timeframe: str = "15m"
    session_name: str = "london"
    instruction_version_id: Optional[int] = None
    custom_instructions: Optional[str] = None
    start_date: datetime
    end_date: datetime

class BacktestResultRead(BaseModel):
    id: int
    symbol: str
    instrument_id: int
    timeframe: str
    session_name: str
    instruction_version_id: Optional[int] = None
    start_date: datetime
    end_date: datetime
    total_candles_analyzed: int
    state_distribution: Dict[str, int] = {}
    identified_setups: List[Dict[str, Any]] = []
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

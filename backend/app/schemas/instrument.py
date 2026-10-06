from datetime import datetime
from pydantic import BaseModel, ConfigDict

class InstrumentBase(BaseModel):
    symbol: str
    base_asset: str
    quote_asset: str
    pip_size: float = 0.0001
    is_active: bool = True

class InstrumentCreate(InstrumentBase):
    pass

class InstrumentRead(InstrumentBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

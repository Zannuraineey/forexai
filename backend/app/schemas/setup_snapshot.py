from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict

class SetupContextSnapshot(BaseModel):
    """
    Comprehensive context snapshot attached to every candidate setup.
    Preserves all conditioning variables (7H Profile, Session, HTF, Structure,
    Liquidity, DXY, News, Target Realism) for deterministic audit and research.
    """
    symbol: str
    timestamp: datetime

    profile: Dict[str, Any] = {}
    session: Dict[str, Any] = {}
    htf: Dict[str, Any] = {}
    structure: Dict[str, Any] = {}
    liquidity: Dict[str, Any] = {}
    dxy: Dict[str, Any] = {}
    news: Dict[str, Any] = {}

    entry: float
    stop_loss: float
    tp1: float
    tp2: float
    tp3: Optional[float] = None

    risk_distance: float
    rr_tp1: float
    rr_tp2: float
    rr_tp3: Optional[float] = None

    target_quality: str # NORMAL_TARGET, EXTENDED_TARGET, EXTREME_TARGET, TARGET_BEYOND_AVAILABLE_CONTEXT
    data_quality: str = "COMPLETE"

    model_config = ConfigDict(from_attributes=True)

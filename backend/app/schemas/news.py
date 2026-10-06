from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class EconomicEvent(BaseModel):
    id: str
    title: str
    country: str = "USD"
    currency: str = "USD"
    impact: str = Field(description="HIGH, MEDIUM, LOW")
    event_time_utc: datetime
    actual: Optional[float] = None
    forecast: Optional[float] = None
    previous: Optional[float] = None
    revised: Optional[float] = None
    unit: str = "%"
    status: str = Field(default="SCHEDULED", description="SCHEDULED, RELEASED, REVISED")
    meaning: str = Field(description="Institutional explanation of what the event measures and why it matters")
    historical_context: str = Field(description="Context regarding recent historical prints and trends")
    historical_reactions: List[Dict[str, Any]] = Field(default_factory=list, description="Past release reaction data")

class DXYMetrics(BaseModel):
    value: float
    change_pct: float
    trend: str = Field(description="BULLISH, BEARISH, CONSOLIDATING")
    market_regime: str = Field(description="RISK_ON, RISK_OFF, NEUTRAL, EXPANSION, CONTRACTION")
    smc_structure: str = Field(description="Detailed SMC market structure e.g. Liquidity Swept, MSS Confirmed, Premium FVG Retest")
    rsi_14: float
    ema_200: float
    displacement_active: bool
    confirmation_status: str = Field(description="CONFIRMING_BULLISH, CONFIRMING_BEARISH, DIVERGENT, NEUTRAL")
    source: str = Field(default="SYNTHETIC_BASKET_DXY", description="Source of calculation")

class PairImpactAnalysis(BaseModel):
    symbol: str
    directional_bias: str = Field(description="BULLISH, BEARISH, NEUTRAL")
    confidence: float = Field(ge=0.0, le=1.0)
    correlation_to_usd: str = Field(description="INVERSE, DIRECT, DECOUPLED")
    smc_confluence: str = Field(description="How pair's SMC structure aligns with USD/DXY trajectory")
    key_levels: Dict[str, float] = Field(default_factory=dict, description="Institutional reference levels SL/TP/Entry/Invalidation")
    trade_thesis: str = Field(description="Institutional reasoning combining Macro + DXY + Local SMC")

class NewsIntelligenceReport(BaseModel):
    id: str
    generated_at_utc: datetime
    event: EconomicEvent
    dxy_context: DXYMetrics
    deviation_analysis: str = Field(description="Analysis of actual vs forecast vs previous outcome")
    historical_comparison: str = Field(description="Comparison to previous relevant macroeconomic prints")
    macro_regime_summary: str = Field(description="Current macroeconomic regime and liquidity condition")
    smc_technical_synthesis: str = Field(description="Combined SMC, market structure, and technical indicators")
    pair_analyses: List[PairImpactAnalysis] = Field(default_factory=list)
    actionable_conclusion: str = Field(description="Clear executive reasoning explaining the complete setup")

class NewsIntelligenceRequest(BaseModel):
    event_id: Optional[str] = None
    user_pairs: List[str] = Field(default_factory=lambda: ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "BTCUSD"])
    custom_notes: Optional[str] = None

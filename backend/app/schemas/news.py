from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class EconomicEvent(BaseModel):
    id: str
    title: str
    country: str = "USD"
    currency: str = "USD"
    impact: str = Field(description="HIGH, MEDIUM, LOW, HOLIDAY")
    event_time_utc: datetime
    actual: Optional[float] = None
    forecast: Optional[float] = None
    previous: Optional[float] = None
    revised: Optional[float] = None
    unit: str = "%"
    status: str = Field(default="SCHEDULED", description="SCHEDULED, RELEASED, REVISED, HOLIDAY")
    meaning: str = Field(description="Institutional explanation of what the event measures and why it matters")
    historical_context: str = Field(description="Context regarding recent historical prints and trends")
    historical_reactions: List[Dict[str, Any]] = Field(default_factory=list, description="Past release reaction data")
    raw_forecast: Optional[str] = None
    raw_previous: Optional[str] = None
    raw_actual: Optional[str] = None

class BreakingNewsItem(BaseModel):
    id: str
    title: str
    summary: str
    source: str
    published_at_utc: datetime
    url: Optional[str] = None
    currencies: List[str] = Field(default_factory=list)
    sentiment: str = Field(default="NEUTRAL", description="BULLISH, BEARISH, NEUTRAL")
    impact: str = Field(default="MEDIUM", description="HIGH, MEDIUM, LOW")

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

class InstitutionalOrderDensity(BaseModel):
    buy_side_liquidity: float = Field(description="Buy-Side Liquidity (BSL) price pool above swing highs")
    sell_side_liquidity: float = Field(description="Sell-Side Liquidity (SSL) price pool below swing lows")
    order_block_zone: str = Field(description="Institutional mitigation/order block price zone")
    order_volume_concentration: str = Field(description="Where massive retail and institutional orders are concentrated")

class InstitutionalManipulationAnalysis(BaseModel):
    judas_swing_risk: str = Field(description="HIGH, MEDIUM, LOW probability of a false initial news breakout")
    trap_type: str = Field(description="BULL_TRAP, BEAR_TRAP, LIQUIDITY_RUN_BOTH_SIDES, DIRECT_EXPANSION")
    manipulation_thesis: str = Field(description="How institutional algorithms manipulate news volume to engineer liquidity")
    reversal_expected: bool = Field(default=True, description="Whether an initial Judas spike is expected to sharply reverse")

class DirectionChangeTiming(BaseModel):
    initial_spike_duration: str = Field(description="Estimated duration of initial chaotic spike (e.g. 0-2 mins post-news)")
    reversal_inflection_window: str = Field(description="Time window when the Judas swing exhausts and direction flips (e.g. 3-7 mins)")
    true_trend_expansion_time: str = Field(description="Time window when the real institutional trend displaces (e.g. 8-25 mins)")
    safe_entry_time: str = Field(description="Safe rule-based execution time (e.g. wait for 5m candle close)")

class OrderPlacementBlueprint(BaseModel):
    action: str = Field(description="BUY_LIMIT_AFTER_SSL_SWEEP, SELL_LIMIT_AFTER_BSL_SWEEP, WAIT_FOR_MSS, STAND_ASIDE")
    recommended_entry: float = Field(description="Precise institutional limit entry price")
    stop_loss: float = Field(description="Protected stop loss level beyond the Judas sweep wick")
    take_profit_1: float = Field(description="Primary take profit targeting opposing liquidity pool")
    take_profit_2: float = Field(description="Runner target at next major liquidity pool")
    risk_reward_ratio: str = Field(default="1:3.0", description="Estimated risk to reward ratio")
    execution_rule: str = Field(description="Concrete non-vague order execution instructions for traders")

class NewsSpikeDetection(BaseModel):
    is_spike_active: bool = Field(description="Whether a high-velocity news spike is actively in progress")
    spike_direction: str = Field(description="BULLISH_SPIKE, BEARISH_SPIKE, WHIPSAW, STABLE")
    estimated_volatility_pips: float = Field(description="Estimated or measured spike displacement in pips")
    spike_status: str = Field(description="Current status of the news spike volatility")

class PairImpactAnalysis(BaseModel):
    symbol: str
    directional_bias: str = Field(description="BULLISH, BEARISH, NEUTRAL")
    confidence: float = Field(ge=0.0, le=1.0)
    correlation_to_usd: str = Field(description="INVERSE, DIRECT, DECOUPLED")
    smc_confluence: str = Field(description="How pair's SMC structure aligns with USD/DXY trajectory")
    key_levels: Dict[str, float] = Field(default_factory=dict, description="Institutional reference levels SL/TP/Entry/Invalidation")
    trade_thesis: str = Field(description="Institutional reasoning combining Macro + DXY + Local SMC")
    order_density: Optional[InstitutionalOrderDensity] = None
    manipulation: Optional[InstitutionalManipulationAnalysis] = None
    reversal_timing: Optional[DirectionChangeTiming] = None
    order_blueprint: Optional[OrderPlacementBlueprint] = None
    spike_analysis: Optional[NewsSpikeDetection] = None

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
    ai_engine_used: Optional[str] = Field(default="QUANT_MACRO_SYNTHESIS", description="AI Provider e.g. Gemini 1.5, OpenAI GPT-4o, or QUANT_MACRO_SYNTHESIS")
    institutional_order_summary: Optional[str] = Field(default=None, description="Executive breakdown of where massive bank orders sit")
    macro_reversal_window: Optional[str] = Field(default=None, description="Global timing window for news spike reversals")
    spike_warning: Optional[str] = Field(default=None, description="Real-time news spike volatility and slippage advisory")

class NewsIntelligenceRequest(BaseModel):
    event_id: Optional[str] = None
    user_pairs: List[str] = Field(default_factory=lambda: ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "BTCUSD"])
    custom_notes: Optional[str] = None
    custom_query: Optional[str] = None
    custom_scenario_event: Optional[EconomicEvent] = None
    custom_api_key: Optional[str] = None
    ai_model: Optional[str] = None

class AIQueryRequest(BaseModel):
    query: str
    user_pairs: List[str] = Field(default_factory=lambda: ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "BTCUSD"])
    custom_api_key: Optional[str] = None
    ai_model: Optional[str] = None

class AIQueryResponse(BaseModel):
    query: str
    ai_analysis: str
    dxy_context: DXYMetrics
    market_regime: str
    pair_analyses: List[PairImpactAnalysis]
    key_takeaways: List[str] = Field(default_factory=list)
    timestamp_utc: datetime
    ai_engine_used: str = "QUANT_MACRO_SYNTHESIS"

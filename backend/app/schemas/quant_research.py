from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class EdgeStatus(str, Enum):
    PROVEN_EDGE = "PROVEN_EDGE"          # N >= min_sample, Expectancy >= +0.35R, p < 0.05
    MODERATE_EDGE = "MODERATE_EDGE"      # N >= min_sample, +0.10R <= Expectancy < +0.35R
    NEUTRAL_EDGE = "NEUTRAL_EDGE"        # N >= min_sample, -0.10R <= Expectancy < +0.10R
    NEGATIVE_EDGE = "NEGATIVE_EDGE"      # N >= min_sample, Expectancy < -0.10R (VETO)
    INSUFFICIENT_SAMPLE = "INSUFFICIENT_SAMPLE"  # N < min_sample (incubating)


class CohortKey(BaseModel):
    """Multivariate conditioning coordinate identifying a specific market regime combination."""
    symbol: Optional[str] = None
    direction: Optional[str] = None
    seven_hour_direction: Optional[str] = None
    seven_hour_classification: Optional[str] = None
    primary_session: Optional[str] = None
    killzone: Optional[str] = None
    dxy_relationship: Optional[str] = None
    liquidity_event: Optional[str] = None
    mss_type: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    def to_compact_string(self) -> str:
        parts = [
            f"Sym:{self.symbol or '*'}",
            f"Dir:{self.direction or '*'}",
            f"7H:{self.seven_hour_direction or '*'}",
            f"Sess:{self.primary_session or '*'}",
            f"DXY:{self.dxy_relationship or '*'}",
            f"Liq:{self.liquidity_event or '*'}",
        ]
        return " | ".join(parts)


class MilestoneDecayCurve(BaseModel):
    """Empirical probabilities P(kR) of price reaching milestone kR before stop loss."""
    p_1r: Optional[float] = None
    p_2r: Optional[float] = None
    p_3r: Optional[float] = None
    p_5r: Optional[float] = None
    p_10r: Optional[float] = None
    p_20r: Optional[float] = None
    optimal_milestone: Optional[str] = None
    optimal_milestone_ev: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class ExcursionMetrics(BaseModel):
    """Distribution of Max Favorable (MFE) and Max Adverse (MAE) excursions in R-multiples."""
    mean_mfe_r: float = 0.0
    median_mfe_r: float = 0.0
    mean_mae_r: float = 0.0
    median_mae_r: float = 0.0
    pct_95_mae_r: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class CohortEdgeResult(BaseModel):
    """Empirical performance metrics and statistical edge diagnosis for a specific cohort."""
    cohort_key: CohortKey
    sample_size: int
    edge_status: EdgeStatus
    win_rate: Optional[float] = None
    loss_rate: Optional[float] = None
    avg_win_r: Optional[float] = None
    avg_loss_r: Optional[float] = None
    mathematical_expectancy: Optional[float] = None
    profit_factor: Optional[float] = None
    z_score: Optional[float] = None
    p_value: Optional[float] = None
    is_statistically_significant: bool = False
    milestones: MilestoneDecayCurve = Field(default_factory=MilestoneDecayCurve)
    excursions: ExcursionMetrics = Field(default_factory=ExcursionMetrics)
    recommendation: str

    model_config = ConfigDict(from_attributes=True)


class QuantResearchReport(BaseModel):
    """Comprehensive empirical research report across all discovered multivariate cohorts."""
    symbol: Optional[str] = None
    total_setups_analyzed: int
    eligible_cohorts_count: int
    proven_edge_cohorts: List[CohortEdgeResult] = Field(default_factory=list)
    toxic_veto_cohorts: List[CohortEdgeResult] = Field(default_factory=list)
    all_cohorts: List[CohortEdgeResult] = Field(default_factory=list)
    generated_at_utc: datetime

    model_config = ConfigDict(from_attributes=True)


class CandidateEdgeEvaluationRequest(BaseModel):
    """Request to evaluate a candidate setup snapshot against empirical cohorts."""
    symbol: str
    direction: str
    setup_snapshot: Dict[str, Any]
    min_sample_size: int = 30

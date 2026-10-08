import math
import statistics
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union, Tuple
from collections import defaultdict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.trade_outcome import TradeSetupOutcome
from app.schemas.quant_research import (
    EdgeStatus,
    CohortKey,
    MilestoneDecayCurve,
    ExcursionMetrics,
    CohortEdgeResult,
    QuantResearchReport,
)


class QuantResearchEngine:
    """
    Quantitative Research Engine for ForexAI.
    
    Transforms discretionary ICT/SMC heuristics into empirically proven trading models.
    Analyzes accumulated TradeSetupOutcome records and multivariate SetupContextSnapshot
    data to discover, measure, and validate genuine statistical edges.

    Core Capabilities:
    - Multivariate Cohort Clustering: (7H Profile × Session × DXY × Liquidity × MSS)
    - Mathematical Expectancy: E = (W * AvgWin) - (L * AvgLoss)
    - Milestone Probability Decay Curves: P(1R) -> P(2R) -> P(3R) -> P(5R) -> P(10R) -> P(20R)
    - Optimal Target Milestone Discovery: argmax_k [k * P(kR)]
    - Statistical Significance: Z-score and two-tailed p-value against baseline
    - Toxic Regime Veto: Flags cohorts with negative expectancy to prevent capital loss
    - Zero Assumption Rule: Flags INSUFFICIENT_SAMPLE when N < min_sample_size (default 30)
    """

    DEFAULT_MIN_SAMPLE_SIZE = 30

    @classmethod
    def extract_cohort_key(cls, setup: Union[TradeSetupOutcome, Dict[str, Any]]) -> CohortKey:
        """Extracts the discrete multivariate conditioning tuple from a trade setup or outcome."""
        if isinstance(setup, dict):
            symbol = setup.get("symbol")
            direction = setup.get("direction")
            snapshot = setup.get("setup_snapshot") or {}
        else:
            symbol = getattr(setup, "symbol", None)
            direction = getattr(setup, "direction", None)
            snapshot = getattr(setup, "setup_snapshot", {}) or {}

        # 7H Profile
        profile_data = snapshot.get("profile") or snapshot.get("seven_hour_profile") or {}
        p_dir = profile_data.get("seven_hour_direction") or profile_data.get("direction") or "NEUTRAL"
        p_class = profile_data.get("seven_hour_classification") or profile_data.get("classification") or "NORMAL"

        # Session & Killzone
        sess_data = snapshot.get("session") or {}
        primary_sess = sess_data.get("primary_session") or "OFF_SESSION"
        kz = sess_data.get("killzone") or "NONE"
        if isinstance(kz, dict):
            kz = kz.get("name", "NONE")

        # DXY Intermarket
        dxy_data = snapshot.get("dxy") or {}
        dxy_rel = dxy_data.get("dxy_relationship_to_symbol") or dxy_data.get("relationship") or "NEUTRAL"

        # Liquidity Sweep
        liq_data = snapshot.get("liquidity") or {}
        liq_event = liq_data.get("event")
        if not liq_event:
            sweeps = liq_data.get("recent_sweeps") or []
            if sweeps:
                liq_event = "SWEEP_OCCURRED"
            else:
                liq_event = "NO_SWEEP"

        # MSS
        struct_data = snapshot.get("structure") or {}
        mss_data = struct_data.get("recent_mss") or []
        mss_type = "MSS_CONFIRMED" if mss_data else "NO_MSS"

        return CohortKey(
            symbol=symbol,
            direction=direction,
            seven_hour_direction=str(p_dir).upper(),
            seven_hour_classification=str(p_class).upper(),
            primary_session=str(primary_sess).upper(),
            killzone=str(kz).upper(),
            dxy_relationship=str(dxy_rel).upper(),
            liquidity_event=str(liq_event).upper(),
            mss_type=str(mss_type).upper(),
        )

    @classmethod
    def calculate_p_value(cls, z: float) -> float:
        """Calculates two-tailed p-value from z-score using complementary error function."""
        try:
            return math.erfc(abs(z) / math.sqrt(2.0))
        except Exception:
            return 1.0

    @classmethod
    def compute_milestone_decay(cls, setups: List[Any]) -> MilestoneDecayCurve:
        """Computes empirical milestone progression P(1R..20R) and optimal EV target."""
        total = len(setups)
        if total == 0:
            return MilestoneDecayCurve()

        count_1r = sum(1 for s in setups if getattr(s, "reached_1r", False) or (isinstance(s, dict) and s.get("reached_1r", False)))
        count_2r = sum(1 for s in setups if getattr(s, "reached_2r", False) or (isinstance(s, dict) and s.get("reached_2r", False)))
        count_3r = sum(1 for s in setups if getattr(s, "reached_3r", False) or (isinstance(s, dict) and s.get("reached_3r", False)))
        count_5r = sum(1 for s in setups if getattr(s, "reached_5r", False) or (isinstance(s, dict) and s.get("reached_5r", False)))
        count_10r = sum(1 for s in setups if getattr(s, "reached_10r", False) or (isinstance(s, dict) and s.get("reached_10r", False)))
        count_20r = sum(1 for s in setups if getattr(s, "reached_20r", False) or (isinstance(s, dict) and s.get("reached_20r", False)))

        p_1r = round(count_1r / total, 4)
        p_2r = round(count_2r / total, 4)
        p_3r = round(count_3r / total, 4)
        p_5r = round(count_5r / total, 4)
        p_10r = round(count_10r / total, 4)
        p_20r = round(count_20r / total, 4)

        # Expected Value at each milestone k: EV(k) = k * P(kR)
        candidates = [
            ("1R", 1.0, 1.0 * p_1r),
            ("2R", 2.0, 2.0 * p_2r),
            ("3R", 3.0, 3.0 * p_3r),
            ("5R", 5.0, 5.0 * p_5r),
            ("10R", 10.0, 10.0 * p_10r),
            ("20R", 20.0, 20.0 * p_20r),
        ]
        best_name, best_k, best_ev = max(candidates, key=lambda x: x[2])

        return MilestoneDecayCurve(
            p_1r=p_1r,
            p_2r=p_2r,
            p_3r=p_3r,
            p_5r=p_5r,
            p_10r=p_10r,
            p_20r=p_20r,
            optimal_milestone=best_name,
            optimal_milestone_ev=round(best_ev, 3),
        )

    @classmethod
    def compute_excursion_metrics(cls, setups: List[Any]) -> ExcursionMetrics:
        """Computes distribution statistics for MFE and MAE in R-multiples."""
        mfes: List[float] = []
        maes: List[float] = []

        for s in setups:
            mfe_val = getattr(s, "mfe_r_multiple", None) if not isinstance(s, dict) else s.get("mfe_r_multiple")
            mae_val = getattr(s, "mae_r_multiple", None) if not isinstance(s, dict) else s.get("mae_r_multiple")
            if mfe_val is not None:
                mfes.append(float(mfe_val))
            if mae_val is not None:
                maes.append(float(mae_val))

        if not mfes or not maes:
            return ExcursionMetrics()

        mean_mfe = round(statistics.mean(mfes), 3)
        median_mfe = round(statistics.median(mfes), 3)
        mean_mae = round(statistics.mean(maes), 3)
        median_mae = round(statistics.median(maes), 3)

        # 95th percentile MAE
        sorted_mae = sorted(maes)
        idx_95 = int(math.ceil(0.95 * len(sorted_mae))) - 1
        pct_95 = round(sorted_mae[max(0, min(idx_95, len(sorted_mae) - 1))], 3)

        return ExcursionMetrics(
            mean_mfe_r=mean_mfe,
            median_mfe_r=median_mfe,
            mean_mae_r=mean_mae,
            median_mae_r=median_mae,
            pct_95_mae_r=pct_95,
        )

    @classmethod
    def evaluate_cohort(
        cls,
        cohort_key: CohortKey,
        setups: List[Any],
        min_sample_size: int = DEFAULT_MIN_SAMPLE_SIZE,
    ) -> CohortEdgeResult:
        """Evaluates a single cohort's sample size, expectancy, edge status, and milestones."""
        n = len(setups)

        # Baseline milestone and excursion calculations
        milestones = cls.compute_milestone_decay(setups)
        excursions = cls.compute_excursion_metrics(setups)

        if n < min_sample_size:
            return CohortEdgeResult(
                cohort_key=cohort_key,
                sample_size=n,
                edge_status=EdgeStatus.INSUFFICIENT_SAMPLE,
                win_rate=None,
                loss_rate=None,
                avg_win_r=None,
                avg_loss_r=None,
                mathematical_expectancy=None,
                profit_factor=None,
                z_score=None,
                p_value=None,
                is_statistically_significant=False,
                milestones=milestones,
                excursions=excursions,
                recommendation=f"INCUBATING: Insufficient sample size ({n}/{min_sample_size}) to establish statistical edge.",
            )

        win_r_list: List[float] = []
        loss_r_list: List[float] = []

        for s in setups:
            outcome = getattr(s, "outcome", None) if not isinstance(s, dict) else s.get("outcome")
            r_val = getattr(s, "realized_r_multiple", None) if not isinstance(s, dict) else s.get("realized_r_multiple")
            if r_val is None:
                continue

            r_float = float(r_val)
            if outcome in ("TP_HIT", "TP1_HIT", "TP2_HIT", "TP3_HIT") or r_float > 0.0:
                win_r_list.append(r_float)
            else:
                loss_r_list.append(abs(r_float))

        total_resolved = len(win_r_list) + len(loss_r_list)
        if total_resolved == 0:
            return CohortEdgeResult(
                cohort_key=cohort_key,
                sample_size=n,
                edge_status=EdgeStatus.INSUFFICIENT_SAMPLE,
                milestones=milestones,
                excursions=excursions,
                recommendation="INSUFFICIENT_DATA: No resolved trade outcomes.",
            )

        win_count = len(win_r_list)
        loss_count = len(loss_r_list)
        win_rate = round(win_count / total_resolved, 4)
        loss_rate = round(loss_count / total_resolved, 4)

        avg_win = round(statistics.mean(win_r_list), 3) if win_r_list else 0.0
        avg_loss = round(statistics.mean(loss_r_list), 3) if loss_r_list else 1.0

        # Mathematical Expectancy: E = (W * avg_win) - (L * avg_loss)
        expectancy = round((win_rate * avg_win) - (loss_rate * avg_loss), 3)

        # Profit Factor
        sum_win = sum(win_r_list)
        sum_loss = sum(loss_r_list)
        profit_factor = round(sum_win / max(sum_loss, 1e-6), 2) if sum_loss > 0 else (99.0 if sum_win > 0 else 0.0)

        # Statistical significance test against random 50% baseline
        p0 = 0.50
        se = math.sqrt((p0 * (1.0 - p0)) / total_resolved)
        z = round((win_rate - p0) / max(se, 1e-6), 3)
        p_val = round(cls.calculate_p_value(z), 4)
        is_significant = (p_val < 0.05) and (z > 0)

        # Edge Classification
        if expectancy >= 0.35 and is_significant:
            edge_status = EdgeStatus.PROVEN_EDGE
            recommendation = (
                f"GRADE_A_PRIME: Proven institutional edge (E = +{expectancy}R, p = {p_val}). "
                f"Optimal target: {milestones.optimal_milestone}."
            )
        elif expectancy >= 0.10:
            edge_status = EdgeStatus.MODERATE_EDGE
            recommendation = f"GRADE_B: Moderate edge (E = +{expectancy}R). Win rate {win_rate * 100:.1f}%."
        elif expectancy >= -0.10:
            edge_status = EdgeStatus.NEUTRAL_EDGE
            recommendation = f"NEUTRAL: Indeterminate break-even noise (E = {expectancy}R). Exercise caution."
        else:
            edge_status = EdgeStatus.NEGATIVE_EDGE
            recommendation = (
                f"VETO: Statistically negative expectancy (E = {expectancy}R, Win rate {win_rate * 100:.1f}%). "
                "Automatically suppress setups in this regime."
            )

        return CohortEdgeResult(
            cohort_key=cohort_key,
            sample_size=n,
            edge_status=edge_status,
            win_rate=win_rate,
            loss_rate=loss_rate,
            avg_win_r=avg_win,
            avg_loss_r=avg_loss,
            mathematical_expectancy=expectancy,
            profit_factor=profit_factor,
            z_score=z,
            p_value=p_val,
            is_statistically_significant=is_significant,
            milestones=milestones,
            excursions=excursions,
            recommendation=recommendation,
        )

    @classmethod
    def analyze_cohorts(
        cls,
        setups_data: List[Union[TradeSetupOutcome, Dict[str, Any]]],
        min_sample_size: int = DEFAULT_MIN_SAMPLE_SIZE,
        symbol_filter: Optional[str] = None,
    ) -> QuantResearchReport:
        """Groups historical trade setups into multivariate cohorts and diagnoses empirical statistical edges."""
        filtered = setups_data
        if symbol_filter:
            sym_up = symbol_filter.upper()
            filtered = [
                s for s in setups_data
                if (getattr(s, "symbol", "") if not isinstance(s, dict) else s.get("symbol", "")).upper() == sym_up
            ]

        # Group by cohort tuple string representation
        cohort_groups = defaultdict(list)
        for s in filtered:
            ck = cls.extract_cohort_key(s)
            key_repr = (
                ck.symbol,
                ck.direction,
                ck.seven_hour_direction,
                ck.primary_session,
                ck.dxy_relationship,
                ck.liquidity_event,
            )
            cohort_groups[key_repr].append((ck, s))

        all_results: List[CohortEdgeResult] = []
        proven_edges: List[CohortEdgeResult] = []
        toxic_vetoes: List[CohortEdgeResult] = []

        for key_tuple, items in cohort_groups.items():
            ck = items[0][0]
            group_setups = [item[1] for item in items]
            res = cls.evaluate_cohort(
                cohort_key=ck,
                setups=group_setups,
                min_sample_size=min_sample_size,
            )
            all_results.append(res)
            if res.edge_status == EdgeStatus.PROVEN_EDGE:
                proven_edges.append(res)
            elif res.edge_status == EdgeStatus.NEGATIVE_EDGE:
                toxic_vetoes.append(res)

        # Sort proven edges by highest mathematical expectancy
        proven_edges.sort(key=lambda x: x.mathematical_expectancy or -99.0, reverse=True)
        toxic_vetoes.sort(key=lambda x: x.mathematical_expectancy or 99.0)

        eligible_count = sum(1 for r in all_results if r.edge_status != EdgeStatus.INSUFFICIENT_SAMPLE)

        return QuantResearchReport(
            symbol=symbol_filter,
            total_setups_analyzed=len(filtered),
            eligible_cohorts_count=eligible_count,
            proven_edge_cohorts=proven_edges,
            toxic_veto_cohorts=toxic_vetoes,
            all_cohorts=all_results,
            generated_at_utc=datetime.now(timezone.utc),
        )

    @classmethod
    def evaluate_candidate_edge(
        cls,
        candidate_symbol: str,
        candidate_direction: str,
        candidate_snapshot: Dict[str, Any],
        historical_setups: List[Union[TradeSetupOutcome, Dict[str, Any]]],
        min_sample_size: int = DEFAULT_MIN_SAMPLE_SIZE,
    ) -> CohortEdgeResult:
        """
        Evaluates an active candidate setup snapshot against accumulated empirical history.
        Determines if the candidate matches a proven edge, a toxic veto cohort, or is incubating.
        """
        candidate_obj = {
            "symbol": candidate_symbol,
            "direction": candidate_direction,
            "setup_snapshot": candidate_snapshot,
        }
        cand_key = cls.extract_cohort_key(candidate_obj)

        # Filter historical setups matching this cohort coordinate
        matching_history: List[Any] = []
        for s in historical_setups:
            s_key = cls.extract_cohort_key(s)
            # Match core predictive dimensions: direction, 7H direction, session, DXY relationship
            if (
                s_key.symbol == cand_key.symbol
                and s_key.direction == cand_key.direction
                and s_key.seven_hour_direction == cand_key.seven_hour_direction
                and s_key.primary_session == cand_key.primary_session
                and s_key.dxy_relationship == cand_key.dxy_relationship
            ):
                matching_history.append(s)

        return cls.evaluate_cohort(
            cohort_key=cand_key,
            setups=matching_history,
            min_sample_size=min_sample_size,
        )

    @classmethod
    async def load_and_analyze_from_db(
        cls,
        db: AsyncSession,
        symbol: Optional[str] = None,
        min_sample_size: int = DEFAULT_MIN_SAMPLE_SIZE,
    ) -> QuantResearchReport:
        """Fetches all closed TradeSetupOutcome records from database and computes research report."""
        stmt = select(TradeSetupOutcome).order_by(desc(TradeSetupOutcome.signal_timestamp_utc))
        if symbol:
            stmt = stmt.where(TradeSetupOutcome.symbol == symbol.upper())

        res = await db.execute(stmt)
        outcomes = list(res.scalars().all())

        return cls.analyze_cohorts(
            setups_data=outcomes,
            min_sample_size=min_sample_size,
            symbol_filter=symbol,
        )

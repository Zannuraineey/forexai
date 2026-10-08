import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.schemas.quant_research import (
    EdgeStatus,
    CohortKey,
    MilestoneDecayCurve,
    ExcursionMetrics,
    CohortEdgeResult,
    QuantResearchReport,
    CandidateEdgeEvaluationRequest,
)
from app.services.quant.quant_research_engine import QuantResearchEngine


# ==============================================================================
# Helper to generate synthetic historical setups
# ==============================================================================
def make_synthetic_setup(
    setup_id: str,
    symbol: str = "EURUSD",
    direction: str = "BUY",
    outcome: str = "TP_HIT",
    realized_r: float = 2.0,
    mfe_r: float = 2.2,
    mae_r: float = 0.25,
    reached_1r: bool = True,
    reached_2r: bool = True,
    reached_3r: bool = False,
    reached_5r: bool = False,
    reached_10r: bool = False,
    reached_20r: bool = False,
    p_dir: str = "BULLISH",
    session: str = "NEW YORK",
    dxy_rel: str = "SUPPORTIVE",
    liq: str = "ASIAN_LOW_SWEPT",
):
    return {
        "setup_id": setup_id,
        "symbol": symbol,
        "direction": direction,
        "outcome": outcome,
        "realized_r_multiple": realized_r,
        "mfe_r_multiple": mfe_r,
        "mae_r_multiple": mae_r,
        "reached_1r": reached_1r,
        "reached_2r": reached_2r,
        "reached_3r": reached_3r,
        "reached_5r": reached_5r,
        "reached_10r": reached_10r,
        "reached_20r": reached_20r,
        "setup_snapshot": {
            "profile": {"seven_hour_direction": p_dir, "seven_hour_classification": "EXPANSION"},
            "session": {"primary_session": session, "killzone": "NY AM"},
            "dxy": {"dxy_relationship_to_symbol": dxy_rel},
            "liquidity": {"event": liq},
            "structure": {"recent_mss": [{"direction": "BULLISH"}]},
        },
    }


# ==============================================================================
# 1. EXTRACT COHORT KEY
# ==============================================================================
def test_1_extract_cohort_key():
    setup = make_synthetic_setup(
        setup_id="s1",
        symbol="XAGUSD",
        direction="BUY",
        p_dir="BEARISH",
        session="NEW YORK",
        dxy_rel="CONTRADICTING",
        liq="ASIAN_LOW_SWEPT",
    )
    key = QuantResearchEngine.extract_cohort_key(setup)
    assert key.symbol == "XAGUSD"
    assert key.direction == "BUY"
    assert key.seven_hour_direction == "BEARISH"
    assert key.primary_session == "NEW YORK"
    assert key.dxy_relationship == "CONTRADICTING"
    assert key.liquidity_event == "ASIAN_LOW_SWEPT"


# ==============================================================================
# 2. INSUFFICIENT SAMPLE SIZE GUARD
# ==============================================================================
def test_2_insufficient_sample_size_guard():
    # Only 10 setups (below default threshold of 30)
    setups = [make_synthetic_setup(f"s_{i}") for i in range(10)]
    ck = QuantResearchEngine.extract_cohort_key(setups[0])
    res = QuantResearchEngine.evaluate_cohort(ck, setups, min_sample_size=30)

    assert res.sample_size == 10
    assert res.edge_status == EdgeStatus.INSUFFICIENT_SAMPLE
    assert res.mathematical_expectancy is None
    assert res.win_rate is None
    assert "INCUBATING" in res.recommendation


# ==============================================================================
# 3. PROVEN EDGE DETECTION (E >= +0.35R, p < 0.05)
# ==============================================================================
def test_3_proven_edge_detection():
    # 40 setups: 28 winners (70% win rate) @ 2.0R, 12 losers @ -1.0R
    setups = []
    for i in range(28):
        setups.append(make_synthetic_setup(f"w_{i}", outcome="TP_HIT", realized_r=2.0))
    for i in range(12):
        setups.append(make_synthetic_setup(f"l_{i}", outcome="SL_HIT", realized_r=-1.0))

    ck = QuantResearchEngine.extract_cohort_key(setups[0])
    res = QuantResearchEngine.evaluate_cohort(ck, setups, min_sample_size=30)

    assert res.sample_size == 40
    assert res.edge_status == EdgeStatus.PROVEN_EDGE
    assert res.win_rate == pytest.approx(0.70, abs=1e-2)
    # Expectancy: (0.70 * 2.0) - (0.30 * 1.0) = 1.40 - 0.30 = +1.10R
    assert res.mathematical_expectancy == pytest.approx(1.10, abs=1e-2)
    assert res.is_statistically_significant is True
    assert res.p_value < 0.05
    assert "GRADE_A_PRIME" in res.recommendation


# ==============================================================================
# 4. TOXIC VETO COHORT DETECTION (E < -0.10R)
# ==============================================================================
def test_4_toxic_veto_detection():
    # 35 setups: 10 winners (28.6% win rate) @ 1.2R, 25 losers @ -1.05R
    setups = []
    for i in range(10):
        setups.append(make_synthetic_setup(f"w_{i}", outcome="TP_HIT", realized_r=1.2))
    for i in range(25):
        setups.append(make_synthetic_setup(f"l_{i}", outcome="SL_HIT", realized_r=-1.05))

    ck = QuantResearchEngine.extract_cohort_key(setups[0])
    res = QuantResearchEngine.evaluate_cohort(ck, setups, min_sample_size=30)

    assert res.sample_size == 35
    assert res.edge_status == EdgeStatus.NEGATIVE_EDGE
    assert res.mathematical_expectancy < -0.10
    assert "VETO" in res.recommendation


# ==============================================================================
# 5. MILESTONE DECAY CURVE AND OPTIMAL TARGET PEAK
# ==============================================================================
def test_5_milestone_decay_curve_and_optimal_target():
    # 100 setups with realistic decay:
    # 1R: 85, 2R: 60, 3R: 45, 5R: 15, 10R: 3, 20R: 1
    setups = []
    for i in range(100):
        setups.append({
            "reached_1r": i < 85,
            "reached_2r": i < 60,
            "reached_3r": i < 45,
            "reached_5r": i < 15,
            "reached_10r": i < 3,
            "reached_20r": i < 1,
        })

    decay = QuantResearchEngine.compute_milestone_decay(setups)

    assert decay.p_1r == 0.85
    assert decay.p_2r == 0.60
    assert decay.p_3r == 0.45
    assert decay.p_5r == 0.15
    assert decay.p_10r == 0.03
    assert decay.p_20r == 0.01

    # EV comparisons:
    # 1R: 1 * 0.85 = 0.85
    # 2R: 2 * 0.60 = 1.20
    # 3R: 3 * 0.45 = 1.35  <-- Optimal EV peak!
    # 5R: 5 * 0.15 = 0.75
    # 20R: 20 * 0.01 = 0.20
    assert decay.optimal_milestone == "3R"
    assert decay.optimal_milestone_ev == 1.35


# ==============================================================================
# 6. EXCURSION METRICS (MFE / MAE)
# ==============================================================================
def test_6_excursion_metrics():
    setups = [
        {"mfe_r_multiple": 1.5, "mae_r_multiple": 0.2},
        {"mfe_r_multiple": 2.5, "mae_r_multiple": 0.4},
        {"mfe_r_multiple": 3.0, "mae_r_multiple": 0.3},
        {"mfe_r_multiple": 0.8, "mae_r_multiple": 0.9},
    ]
    metrics = QuantResearchEngine.compute_excursion_metrics(setups)
    assert metrics.mean_mfe_r == pytest.approx(1.95, abs=1e-2)
    assert metrics.median_mae_r == pytest.approx(0.35, abs=1e-2)
    assert metrics.pct_95_mae_r <= 0.90


# ==============================================================================
# 7. ANALYZE COHORTS GROUPING AND REPORTING
# ==============================================================================
def test_7_analyze_cohorts_grouping():
    # Create 35 setups in Cohort A (Bullish NY) and 35 in Cohort B (Bearish Asian)
    setups = []
    for i in range(35):
        setups.append(make_synthetic_setup(f"a_{i}", session="NEW YORK", outcome="TP_HIT", realized_r=2.0))
    for i in range(35):
        setups.append(make_synthetic_setup(f"b_{i}", session="ASIAN", outcome="SL_HIT", realized_r=-1.0))

    report = QuantResearchEngine.analyze_cohorts(setups, min_sample_size=30)

    assert report.total_setups_analyzed == 70
    assert report.eligible_cohorts_count >= 2
    assert len(report.proven_edge_cohorts) >= 1
    assert len(report.toxic_veto_cohorts) >= 1


# ==============================================================================
# 8. CANDIDATE EDGE EVALUATION MATCHING
# ==============================================================================
def test_8_candidate_edge_evaluation():
    # Generate historical database setups
    history = []
    for i in range(35):
        history.append(make_synthetic_setup(
            f"h_{i}",
            symbol="EURUSD",
            direction="BUY",
            p_dir="BULLISH",
            session="NEW YORK",
            dxy_rel="SUPPORTIVE",
            outcome="TP_HIT",
            realized_r=2.0,
        ))

    # Evaluate candidate setup matching this exact cohort
    candidate_snap = {
        "profile": {"seven_hour_direction": "BULLISH"},
        "session": {"primary_session": "NEW YORK"},
        "dxy": {"dxy_relationship_to_symbol": "SUPPORTIVE"},
    }

    edge = QuantResearchEngine.evaluate_candidate_edge(
        candidate_symbol="EURUSD",
        candidate_direction="BUY",
        candidate_snapshot=candidate_snap,
        historical_setups=history,
        min_sample_size=30,
    )

    assert edge.sample_size == 35
    assert edge.edge_status == EdgeStatus.PROVEN_EDGE
    assert edge.mathematical_expectancy > 0.35


# ==============================================================================
# 9. FASTAPI ENDPOINT VERIFICATION
# ==============================================================================
@pytest.mark.asyncio
async def test_9_quant_research_api_endpoints(db_session):
    from app.core.database import get_db
    app.dependency_overrides[get_db] = lambda: db_session
    transport = ASGITransport(app=app)

    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # GET /api/v1/quant/research
            res = await client.get("/api/v1/quant/research?min_sample=5")
            assert res.status_code == 200
            data = res.json()
            assert "total_setups_analyzed" in data
            assert "proven_edge_cohorts" in data
            assert "toxic_veto_cohorts" in data

            # POST /api/v1/quant/evaluate-candidate
            cand_payload = {
                "symbol": "EURUSD",
                "direction": "BUY",
                "setup_snapshot": {
                    "profile": {"seven_hour_direction": "BULLISH"},
                    "session": {"primary_session": "NEW YORK"},
                    "dxy": {"dxy_relationship_to_symbol": "SUPPORTIVE"},
                },
                "min_sample_size": 10,
            }
            res_post = await client.post("/api/v1/quant/evaluate-candidate", json=cand_payload)
            assert res_post.status_code == 200
            edge_data = res_post.json()
            assert "edge_status" in edge_data
            assert "sample_size" in edge_data
    finally:
        app.dependency_overrides.clear()

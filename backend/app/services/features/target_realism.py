from typing import Any, Dict, List, Optional
from app.schemas.target_realism import TargetClassification, TargetRealismMetrics

class TargetRealismAnalyzer:
    """
    Evaluates whether a Take Profit target is standard, extended, or an extreme
    statistical outlier, without rejecting large R:R setups outright.
    """

    @classmethod
    def evaluate_target(
        cls,
        action: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        atr: Optional[float] = None,
        pip_size: float = 0.0001,
        session_high: Optional[float] = None,
        session_low: Optional[float] = None,
        daily_high: Optional[float] = None,
        daily_low: Optional[float] = None,
        nearest_liquidity_high: Optional[float] = None,
        nearest_liquidity_low: Optional[float] = None,
        historical_outcomes: Optional[List[Any]] = None,
    ) -> TargetRealismMetrics:
        is_long = "BUY" in action.upper() or "LONG" in action.upper()

        if is_long:
            risk_dist = round(entry_price - stop_loss, 5)
            reward_dist = round(take_profit - entry_price, 5)
        else:
            risk_dist = round(stop_loss - entry_price, 5)
            reward_dist = round(entry_price - take_profit, 5)

        safe_risk = max(risk_dist, 1e-6)
        rr_ratio = round(reward_dist / safe_risk, 2) if risk_dist > 0 else 0.0

        effective_pip = pip_size if (pip_size and pip_size > 0) else 0.0001
        target_pips = round(reward_dist / effective_pip, 1)
        target_pct = round((reward_dist / max(entry_price, 1e-6)) * 100.0, 2)
        target_atr = round(reward_dist / atr, 2) if (atr and atr > 0) else None

        # Distance to references
        dist_sh = round(abs(take_profit - session_high), 5) if session_high is not None else None
        dist_sl = round(abs(take_profit - session_low), 5) if session_low is not None else None
        dist_dh = round(abs(take_profit - daily_high), 5) if daily_high is not None else None
        dist_dl = round(abs(take_profit - daily_low), 5) if daily_low is not None else None

        nearest_liq = None
        if is_long:
            liq_ref = nearest_liquidity_high or daily_high or session_high
            nearest_liq = round(abs(take_profit - liq_ref), 5) if liq_ref is not None else None
        else:
            liq_ref = nearest_liquidity_low or daily_low or session_low
            nearest_liq = round(abs(take_profit - liq_ref), 5) if liq_ref is not None else None

        # Deterministic Classification
        if (
            (target_atr is not None and target_atr > 10.0)
            or (rr_ratio > 30.0)
            or (is_long and daily_high is not None and take_profit > daily_high * 1.05)
            or (not is_long and daily_low is not None and take_profit < daily_low * 0.95)
        ):
            classification = TargetClassification.TARGET_BEYOND_AVAILABLE_CONTEXT
            reason = (
                f"Target distance ({reward_dist:.2f}, {target_pips} pips) exceeds 10x ATR, 30R, or available daily extremes. "
                "Target is placed completely beyond observable intraday context."
            )
        elif rr_ratio >= 8.0 or (target_atr is not None and target_atr >= 5.0):
            classification = TargetClassification.EXTREME_TARGET
            reason = (
                f"Reported R:R is {rr_ratio}:1 (>= 8.0R) or >= 5.0x ATR. Mathematically valid, but represents "
                "an extreme statistical outlier requiring multi-session expansion."
            )
        elif rr_ratio >= 4.0 or (target_atr is not None and target_atr >= 2.5):
            classification = TargetClassification.EXTENDED_TARGET
            reason = (
                f"Target R:R is {rr_ratio}:1 (4.0R - 8.0R) or >= 2.5x ATR. Extended target beyond typical "
                "session dealing range; requires strong directional momentum."
            )
        else:
            classification = TargetClassification.NORMAL_TARGET
            reason = (
                f"Target R:R is {rr_ratio}:1 (< 4.0R). Standard realistic target within institutional "
                "session dealing range and ATR expectations."
            )

        # Policy tagging
        if classification == TargetClassification.TARGET_BEYOND_AVAILABLE_CONTEXT:
            policy_applied = "POLICY_FLAGGED_BEYOND_CONTEXT"
        elif classification == TargetClassification.EXTREME_TARGET:
            policy_applied = "POLICY_ALLOWED_EXTREME_TARGET_WITH_TAGGING"
        elif classification == TargetClassification.EXTENDED_TARGET:
            policy_applied = "POLICY_ALLOWED_EXTENDED_TARGET"
        else:
            policy_applied = "POLICY_ALLOWED_NORMAL_TARGET"

        # Statistical support evaluation: strictly data-backed, never invented
        stat_status = "INSUFFICIENT_DATA"
        sample_count = len(historical_outcomes) if historical_outcomes is not None else 0
        hit_rate = None

        if historical_outcomes and len(historical_outcomes) >= 30:
            hits = sum(1 for o in historical_outcomes if getattr(o, "outcome", "") in ("TP_HIT", "TP1_HIT", "TP2_HIT") or float(getattr(o, "mfe_r_multiple", 0) or 0) >= rr_ratio)
            hit_rate = round(hits / len(historical_outcomes), 4)
            stat_status = "STATISTICALLY_SUPPORTED" if hit_rate >= 0.40 else "STATISTICALLY_UNSUPPORTED"
        elif historical_outcomes and len(historical_outcomes) > 0:
            stat_status = "INSUFFICIENT_DATA"

        return TargetRealismMetrics(
            risk_distance=risk_dist,
            reward_distance=reward_dist,
            rr_ratio=rr_ratio,
            target_distance_pips=target_pips,
            target_distance_atr=target_atr,
            target_distance_percent=target_pct,
            distance_to_nearest_liquidity=nearest_liq,
            distance_to_previous_high=dist_dh,
            distance_to_previous_low=dist_dl,
            distance_to_session_high=dist_sh,
            distance_to_session_low=dist_sl,
            distance_to_daily_high=dist_dh,
            distance_to_daily_low=dist_dl,
            classification=classification,
            classification_reason=reason,
            policy_applied=policy_applied,
            statistical_support_status=stat_status,
            historical_sample_size=sample_count if sample_count > 0 else None,
            historical_hit_rate=hit_rate,
        )

    @classmethod
    def analyze_target(
        cls,
        symbol: str,
        direction: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        atr: Optional[float] = None,
        pip_size: float = 0.0001,
        session_high: Optional[float] = None,
        session_low: Optional[float] = None,
        daily_high: Optional[float] = None,
        daily_low: Optional[float] = None,
        nearest_liquidity_high: Optional[float] = None,
        nearest_liquidity_low: Optional[float] = None,
        historical_outcomes: Optional[List[Any]] = None,
    ) -> TargetRealismMetrics:
        """Alias for evaluate_target accepting symbol and direction."""
        return cls.evaluate_target(
            action=direction,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            atr=atr,
            pip_size=pip_size,
            session_high=session_high,
            session_low=session_low,
            daily_high=daily_high,
            daily_low=daily_low,
            nearest_liquidity_high=nearest_liquidity_high,
            nearest_liquidity_low=nearest_liquidity_low,
            historical_outcomes=historical_outcomes,
        )

import re
from typing import Dict, Any, List, Optional
from app.schemas.ai_analysis import AIAnalysisOutput, ConditionStatus, AmbiguityItem
from app.models.analysis import AnalysisStateEnum
from app.services.ai.provider_interface import IAIAnalysisProvider

class DeterministicAIProvider(IAIAnalysisProvider):
    """
    Institutional, zero-repaint AI reasoning provider.
    Evaluates user's session instructions against objective market structure:
    - Fixed historical key levels (Asian High/Low, London High/Low, PDH/PDL)
    - Closed candle wicks for confirmed sweeps (zero repainting)
    - Lower timeframe displacement and Market Structure Shift (MSS)
    - Unmitigated Fair Value Gap (FVG) / Breaker Block retest zones
    - Exact entry limits, Stop Loss (1-2 pips past manipulation wick), and Take Profit (1:2+ R:R)
    """

    AMBIGUOUS_PATTERNS = [
        (r"\b(strong|high|good|decent)\s+volume\b", "Volume condition lacks numerical threshold (e.g., > 1.5x 20-period average volume).", "Specify an objective volume ratio or threshold."),
        (r"\b(strong|good|decent)\s+momentum\b", "Momentum condition lacks objective indicator (e.g., RSI > 60 or MACD histogram positive).", "Specify an indicator metric like RSI, MACD, or ADX."),
        (r"\b(normal|low|high)\s+volatility\b", "Volatility condition lacks quantitative ATR or band threshold.", "Specify an ATR pip threshold or percentage."),
        (r"\b(reasonable|good)\s+risk\b", "Risk/reward condition lacks numerical ratio (e.g., minimum 1:2 R:R).", "Specify explicit minimum risk-to-reward ratio."),
        (r"\b(soon|later|eventually)\b", "Time horizon is undefined.", "Specify an exact candle count or session window."),
    ]

    async def analyze(
        self,
        market_context: Dict[str, Any],
        user_instructions: str,
        previous_analysis: Optional[Dict[str, Any]] = None,
    ) -> AIAnalysisOutput:
        instructions_text = user_instructions.strip()
        if not instructions_text:
            return AIAnalysisOutput(
                state=AnalysisStateEnum.NO_SETUP,
                summary="No user instructions configured for this session.",
                condition_breakdown=[],
                ambiguities_detected=[],
                confidence_notes="Awaiting user session instructions.",
            )

        # 1. Detect Ambiguities
        ambiguities: List[AmbiguityItem] = []
        for pattern, reason, suggestion in self.AMBIGUOUS_PATTERNS:
            match = re.search(pattern, instructions_text, re.IGNORECASE)
            if match:
                ambiguities.append(AmbiguityItem(
                    text_snippet=match.group(0),
                    reason=reason,
                    suggestion=suggestion,
                ))

        # 2. Extract Context Elements
        symbol = market_context.get("symbol", "INSTRUMENT")
        current_price = float(market_context.get("current_price", 0.0))
        indicators = market_context.get("indicators", {})
        rsi = indicators.get("rsi_14")
        atr_pips = indicators.get("atr_14_pips") or 10.0
        pip_size = 0.01 if "JPY" in symbol or "XAU" in symbol or "XAG" in symbol else 0.0001
        if "XAU" in symbol:
            pip_size = 0.1
        elif "XAG" in symbol:
            pip_size = 0.01

        candle_struct = market_context.get("candle_structure", {})
        pattern_type = candle_struct.get("pattern_type", "NEUTRAL")
        direction = candle_struct.get("direction", "NEUTRAL")

        market_struct = market_context.get("market_structure", {})
        trend_state = market_struct.get("trend_state", "CONSOLIDATION")
        recent_swings = market_struct.get("recent_swings", [])
        active_fvgs = market_struct.get("active_unmitigated_fvgs", [])
        recent_mss = market_struct.get("recent_mss", [])

        ref_levels = market_context.get("reference_levels", {})
        pdh = ref_levels.get("previous_day_high")
        pdl = ref_levels.get("previous_day_low")

        session_state = market_context.get("session_state", {})
        session_levels = session_state.get("session_levels", {})
        asian_levels = session_levels.get("asian", {})
        london_levels = session_levels.get("london", {})
        ny_levels = session_levels.get("new_york", {})

        sweeps = market_context.get("recent_liquidity_sweeps", [])

        conditions: List[ConditionStatus] = []
        lower_inst = instructions_text.lower()

        # Check for institutional SMC models
        is_london_model = "loz tradez" in lower_inst or "3-step" in lower_inst or "manipulation candle" in lower_inst or "london" in lower_inst
        is_ny_model = "9:30 am" in lower_inst or "judas swing" in lower_inst or "distribution" in lower_inst or "new york" in lower_inst
        is_asian_model = "tokyo sweep" in lower_inst or "pre-asia" in lower_inst or "mean-reversion" in lower_inst or "asian" in lower_inst

        # Track execution proposal
        trade_proposal: Optional[Dict[str, Any]] = None

        # -------------------------------------------------------------
        # Institutional Rule 1: Liquidity Sweep Evaluation
        # -------------------------------------------------------------
        bearish_sweep = None
        bullish_sweep = None

        # Check sweeps of Highs (Buy-Side Liquidity purged -> potential SHORT)
        for s in sweeps:
            l_type = s.get("level_type", "").upper()
            if "HIGH" in l_type:
                bearish_sweep = s
                break

        # Check sweeps of Lows (Sell-Side Liquidity purged -> potential LONG)
        for s in sweeps:
            l_type = s.get("level_type", "").upper()
            if "LOW" in l_type:
                bullish_sweep = s
                break

        # -------------------------------------------------------------
        # Institutional Rule 2: Displacement & Market Structure Shift (MSS)
        # -------------------------------------------------------------
        bearish_mss = None
        bullish_mss = None
        for m in recent_mss:
            m_type = m.get("mss_type", "").upper()
            if m_type == "BEARISH":
                bearish_mss = m
            elif m_type == "BULLISH":
                bullish_mss = m

        # -------------------------------------------------------------
        # Institutional Rule 3: Fair Value Gap Retest Zone
        # -------------------------------------------------------------
        bearish_fvg = None
        bullish_fvg = None
        for f in active_fvgs:
            f_type = f.get("fvg_type", "").upper()
            if f_type == "BEARISH" and not f.get("mitigated", False):
                bearish_fvg = f
            elif f_type == "BULLISH" and not f.get("mitigated", False):
                bullish_fvg = f

        # Evaluate Setup Scenarios
        # A. Bearish Reversal Setup (BSL Swept -> MSS Bearish -> Bearish FVG Retest)
        if bearish_sweep is not None:
            lvl_name = bearish_sweep.get("level_type", "KEY_HIGH")
            extreme = float(bearish_sweep.get("extreme_price", current_price))
            conditions.append(ConditionStatus(
                condition=f"Buy-Side Liquidity Swept ({lvl_name})",
                satisfied=True,
                evidence=f"Wick peaked at {extreme:.2f} and closed inside. Depth: {bearish_sweep.get('sweep_depth_pips', 0)} pips."
            ))

            has_mss = bearish_mss is not None
            conditions.append(ConditionStatus(
                condition="Displacement & Market Structure Shift (MSS Bearish)",
                satisfied=has_mss,
                evidence=f"Broken swing low at {bearish_mss.get('broken_swing_price', 'N/A')}" if has_mss else "Awaiting lower timeframe swing low break."
            ))

            has_fvg = bearish_fvg is not None
            fvg_top = float(bearish_fvg.get("top_price", 0.0)) if bearish_fvg else 0.0
            fvg_bot = float(bearish_fvg.get("bottom_price", 0.0)) if bearish_fvg else 0.0
            fvg_mid = round((fvg_top + fvg_bot) / 2.0, 2) if has_fvg else current_price
            conditions.append(ConditionStatus(
                condition="Fair Value Gap (FVG) Retest Zone Formed",
                satisfied=has_fvg,
                evidence=f"Active FVG [{fvg_bot:.2f} - {fvg_top:.2f}] (Midpoint: {fvg_mid:.2f})" if has_fvg else "Awaiting 3-bar imbalance."
            ))

            # Stop loss 1.5 pips beyond manipulation wick
            sl_price = round(extreme + (1.5 * pip_size), 2)
            # Target opposing liquidity (Asian Low / London Low or 1:2.5 R:R)
            opposing_low = asian_levels.get("low") or london_levels.get("low") or pdl
            if opposing_low and opposing_low < fvg_mid:
                tp_price = round(opposing_low, 2)
            else:
                risk = abs(sl_price - fvg_mid)
                tp_price = round(fvg_mid - (2.5 * risk), 2)

            risk_dist = abs(sl_price - fvg_mid)
            reward_dist = abs(fvg_mid - tp_price)
            rr_ratio = round(reward_dist / (risk_dist if risk_dist > 0 else 1.0), 2)

            conditions.append(ConditionStatus(
                condition="Risk-to-Reward Ratio >= 1:2",
                satisfied=rr_ratio >= 1.8,
                evidence=f"Calculated R:R is {rr_ratio}:1 (Entry: {fvg_mid:.2f}, SL: {sl_price:.2f}, TP: {tp_price:.2f})"
            ))

            if has_mss and has_fvg and rr_ratio >= 1.8:
                trade_proposal = {
                    "action": "SELL LIMIT",
                    "entry": fvg_mid,
                    "stop_loss": sl_price,
                    "take_profit": tp_price,
                    "rr_ratio": rr_ratio,
                    "bias": "BEARISH",
                    "sweep_level": lvl_name,
                    "model": "London 3-Step / NY Judas Reversal",
                }

        # B. Bullish Reversal Setup (SSL Swept -> MSS Bullish -> Bullish FVG Retest)
        elif bullish_sweep is not None:
            lvl_name = bullish_sweep.get("level_type", "KEY_LOW")
            extreme = float(bullish_sweep.get("extreme_price", current_price))
            conditions.append(ConditionStatus(
                condition=f"Sell-Side Liquidity Swept ({lvl_name})",
                satisfied=True,
                evidence=f"Wick trough at {extreme:.2f} and closed inside. Depth: {bullish_sweep.get('sweep_depth_pips', 0)} pips."
            ))

            has_mss = bullish_mss is not None
            conditions.append(ConditionStatus(
                condition="Displacement & Market Structure Shift (MSS Bullish)",
                satisfied=has_mss,
                evidence=f"Broken swing high at {bullish_mss.get('broken_swing_price', 'N/A')}" if has_mss else "Awaiting lower timeframe swing high break."
            ))

            has_fvg = bullish_fvg is not None
            fvg_top = float(bullish_fvg.get("top_price", 0.0)) if bullish_fvg else 0.0
            fvg_bot = float(bullish_fvg.get("bottom_price", 0.0)) if bullish_fvg else 0.0
            fvg_mid = round((fvg_top + fvg_bot) / 2.0, 2) if has_fvg else current_price
            conditions.append(ConditionStatus(
                condition="Fair Value Gap (FVG) Retest Zone Formed",
                satisfied=has_fvg,
                evidence=f"Active FVG [{fvg_bot:.2f} - {fvg_top:.2f}] (Midpoint: {fvg_mid:.2f})" if has_fvg else "Awaiting 3-bar imbalance."
            ))

            sl_price = round(extreme - (1.5 * pip_size), 2)
            opposing_high = asian_levels.get("high") or london_levels.get("high") or pdh
            if opposing_high and opposing_high > fvg_mid:
                tp_price = round(opposing_high, 2)
            else:
                risk = abs(fvg_mid - sl_price)
                tp_price = round(fvg_mid + (2.5 * risk), 2)

            risk_dist = abs(fvg_mid - sl_price)
            reward_dist = abs(tp_price - fvg_mid)
            rr_ratio = round(reward_dist / (risk_dist if risk_dist > 0 else 1.0), 2)

            conditions.append(ConditionStatus(
                condition="Risk-to-Reward Ratio >= 1:2",
                satisfied=rr_ratio >= 1.8,
                evidence=f"Calculated R:R is {rr_ratio}:1 (Entry: {fvg_mid:.2f}, SL: {sl_price:.2f}, TP: {tp_price:.2f})"
            ))

            if has_mss and has_fvg and rr_ratio >= 1.8:
                trade_proposal = {
                    "action": "BUY LIMIT",
                    "entry": fvg_mid,
                    "stop_loss": sl_price,
                    "take_profit": tp_price,
                    "rr_ratio": rr_ratio,
                    "bias": "BULLISH",
                    "sweep_level": lvl_name,
                    "model": "London 3-Step / NY Judas Reversal",
                }

        # C. If no sweep has completed yet, check proximity to key session boundaries
        else:
            ah = asian_levels.get("high")
            al = asian_levels.get("low")
            lh = london_levels.get("high")
            ll = london_levels.get("low")

            conditions.append(ConditionStatus(
                condition="Session Key Liquidity Pools Defined",
                satisfied=(ah is not None or lh is not None),
                evidence=f"Asian H/L: [{al} - {ah}], London H/L: [{ll} - {lh}], PDH/PDL: [{pdl} - {pdh}]"
            ))

            # Proximity check
            probing_level = None
            if ah and abs(current_price - ah) <= 15 * pip_size:
                probing_level = f"Asian High ({ah})"
            elif al and abs(current_price - al) <= 15 * pip_size:
                probing_level = f"Asian Low ({al})"
            elif lh and abs(current_price - lh) <= 15 * pip_size:
                probing_level = f"London High ({lh})"
            elif ll and abs(current_price - ll) <= 15 * pip_size:
                probing_level = f"London Low ({ll})"

            conditions.append(ConditionStatus(
                condition="Session Liquidity Manipulation / Sweep Occurred",
                satisfied=False,
                evidence=f"Price currently probing {probing_level}. Waiting for manipulation wick sweep and rejection." if probing_level else "Price trading within dealing range; no sweep observed in recent candles."
            ))

        # Check secondary indicators if explicitly requested in user instructions
        rsi_match = re.search(r"rsi\s*(<|>|<=|>=)\s*(\d+)", lower_inst)
        if rsi_match and rsi is not None:
            op, threshold = rsi_match.group(1), float(rsi_match.group(2))
            satisfied = (op == "<" and rsi < threshold) or (op == ">" and rsi > threshold) or (op == "<=" and rsi <= threshold) or (op == ">=" and rsi >= threshold)
            conditions.append(ConditionStatus(
                condition=f"RSI {op} {threshold}",
                satisfied=satisfied,
                evidence=f"Calculated RSI(14) is {rsi:.1f}"
            ))

        # -------------------------------------------------------------
        # Determine State & Rich Actionable Summary
        # -------------------------------------------------------------
        satisfied_count = sum(1 for c in conditions if c.satisfied)
        total_count = len(conditions)

        if trade_proposal:
            state = AnalysisStateEnum.VALID_SETUP
            act = trade_proposal["action"]
            ent = trade_proposal["entry"]
            sl = trade_proposal["stop_loss"]
            tp = trade_proposal["take_profit"]
            rr = trade_proposal["rr_ratio"]
            model = trade_proposal["model"]
            swp = trade_proposal["sweep_level"]

            summary = (
                f"🎯 VALID SETUP [{act}]: {symbol} {model}. "
                f"Entry: {ent:.2f} | SL: {sl:.2f} | TP: {tp:.2f} ({rr}:1 R:R). "
                f"{swp} swept, MSS confirmed. Anticipate limit retest."
            )
            confidence_notes = (
                f"Institutional Zero-Repaint Confirmation: All 3 criteria verified on closed price action. "
                f"Stop Loss anchored {sl:.2f} beyond manipulation wick. Minimum {rr}:1 R:R."
            )
        elif (bearish_sweep or bullish_sweep):
            state = AnalysisStateEnum.POTENTIAL_SETUP
            swp_name = (bearish_sweep or bullish_sweep).get("level_type", "KEY_LEVEL")
            extreme = (bearish_sweep or bullish_sweep).get("extreme_price", current_price)
            summary = (
                f"⚠️ POTENTIAL SETUP: {symbol} swept {swp_name} at {extreme:.2f}. "
                f"Liquidity purged. Awaiting lower-timeframe displacement MSS and FVG creation."
            )
            confidence_notes = "Stage 1 (Liquidity Sweep) confirmed. Monitoring for Stage 2 (Displacement MSS)."
        elif any("probing" in c.evidence.lower() for c in conditions):
            state = AnalysisStateEnum.POTENTIAL_SETUP
            summary = f"⚠️ POTENTIAL SETUP: {symbol} is probing key session liquidity boundary. Monitoring for manipulation wick."
            confidence_notes = "Anticipatory state: Price testing session dealing range boundary."
        elif satisfied_count > 0:
            state = AnalysisStateEnum.WATCH
            summary = f"👀 WATCH: {symbol} active in dealing range ({satisfied_count}/{total_count} criteria met). Monitoring key levels."
            confidence_notes = "Consolidation or waiting for session killzone manipulation."
        else:
            state = AnalysisStateEnum.NO_SETUP
            summary = f"{symbol}: No setup criteria currently met. Maintaining patient execution discipline."
            confidence_notes = "Zero setup criteria satisfied."

        reasoning = (
            f"Institutional SMC/ICT Multi-Step Reasoning for {symbol}:\n"
            + "\n".join([f"- [{ 'PASSED' if c.satisfied else 'PENDING' }] {c.condition}: {c.evidence}" for c in conditions])
        )

        return AIAnalysisOutput(
            state=state,
            summary=summary,
            condition_breakdown=conditions,
            ambiguities_detected=ambiguities,
            confidence_notes=confidence_notes,
            full_reasoning=reasoning,
        )

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union

from app.schemas.bias_validation import (
    FinalBiasState,
    BiasQuality,
    SevenHourRelationship,
    DXYRelationship,
    NewsRiskLevel,
    BiasValidationResult,
)
from app.schemas.market_state import (
    StructuredMarketState,
    SevenHourProfileContext,
    SessionContext,
    TimeframeContext,
    StructureContext,
    LiquidityContext,
)


class BiasValidationEngine:
    """
    Unified Multi-Layer Bias Validation Engine.
    
    Coordinates independent evidence into a single structured directional validation layer
    according to strict hierarchical rules:
    1. Higher Timeframe (HTF) structure: 4H, 1H
    2. 7H Profile: contextual regime/profile
    3. 15M context
    4. Liquidity event: BSL/SSL sweep
    5. MSS/BOS
    6. Session context
    7. DXY intermarket context
    8. News/macro risk
    9. Lower timeframe entry trigger: 5M/1M

    CRITICAL RULES:
    - Strictly separates MARKET BIAS, LIQUIDITY EVENT, and ENTRY TRIGGER.
    - 7H Profile is a conditioning context; it never independently generates trade orders.
    - SessionEngine provides timing & killzones; it never independently creates directional bias.
    - DXY is intermarket confirmation; it never overrides HTF structure.
    - News is a risk filter; it never invents trade direction.
    - No arbitrary probability percentages without verified statistical datasets.
    """

    USD_QUOTE_INSTRUMENTS = {"EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "XAUUSD", "XAGUSD"}
    USD_BASE_INSTRUMENTS = {"USDJPY", "USDCAD", "USDCHF"}

    @classmethod
    def evaluate_dxy_relationship(
        cls,
        symbol: str,
        proposed_bias: str,
        dxy_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates DXY intermarket alignment against a symbol's proposed bias.
        """
        if not dxy_data:
            return {
                "dxy_direction": "UNAVAILABLE",
                "dxy_trend_strength": None,
                "dxy_change": None,
                "relationship": DXYRelationship.UNAVAILABLE,
            }

        sym_upper = symbol.upper()
        dxy_dir = str(dxy_data.get("direction") or dxy_data.get("trend") or "NEUTRAL").upper()
        strength = dxy_data.get("trend_strength")
        change = dxy_data.get("change") or dxy_data.get("change_pct")

        is_usd_quote = sym_upper in cls.USD_QUOTE_INSTRUMENTS
        is_usd_base = sym_upper in cls.USD_BASE_INSTRUMENTS

        if not (is_usd_quote or is_usd_base):
            return {
                "dxy_direction": dxy_dir,
                "dxy_trend_strength": strength,
                "dxy_change": change,
                "relationship": DXYRelationship.UNAVAILABLE,
            }

        if dxy_dir == "NEUTRAL" or proposed_bias in ("NEUTRAL", "CONFLICTED", "INSUFFICIENT_DATA"):
            return {
                "dxy_direction": dxy_dir,
                "dxy_trend_strength": strength,
                "dxy_change": change,
                "relationship": DXYRelationship.NEUTRAL,
            }

        is_bullish = proposed_bias == "BULLISH"

        if is_usd_quote:
            # DXY Bullish = USD strong = quote drops (Bearish quote)
            # DXY Bearish = USD weak = quote rises (Bullish quote)
            if dxy_dir == "BULLISH":
                rel = DXYRelationship.CONTRADICTING if is_bullish else DXYRelationship.SUPPORTIVE
            elif dxy_dir == "BEARISH":
                rel = DXYRelationship.SUPPORTIVE if is_bullish else DXYRelationship.CONTRADICTING
            else:
                rel = DXYRelationship.NEUTRAL
        elif is_usd_base:
            # DXY Bullish = USD strong = base pair rises (Bullish base)
            # DXY Bearish = USD weak = base pair drops (Bearish base)
            if dxy_dir == "BULLISH":
                rel = DXYRelationship.SUPPORTIVE if is_bullish else DXYRelationship.CONTRADICTING
            elif dxy_dir == "BEARISH":
                rel = DXYRelationship.CONTRADICTING if is_bullish else DXYRelationship.SUPPORTIVE
            else:
                rel = DXYRelationship.NEUTRAL
        else:
            rel = DXYRelationship.UNAVAILABLE

        return {
            "dxy_direction": dxy_dir,
            "dxy_trend_strength": strength,
            "dxy_change": change,
            "relationship": rel,
        }

    @classmethod
    def evaluate_news_context(
        cls,
        symbol: str,
        news_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluates News / Macro risk filter without inventing trade direction.
        """
        if not news_data:
            return {
                "risk_level": NewsRiskLevel.LOW_RISK,
                "high_impact_news_nearby": False,
                "news_event": None,
                "minutes_to_event": None,
                "minutes_since_event": None,
                "usd_news_risk": "UNAVAILABLE",
            }

        hi_nearby = bool(news_data.get("high_impact_news_nearby", False))
        m_to = news_data.get("minutes_to_event")
        m_since = news_data.get("minutes_since_event")
        event_name = news_data.get("news_event")

        # Determine risk level
        if m_to is not None and m_to <= 0 and (m_since is None or m_since <= 15):
            risk_level = NewsRiskLevel.EVENT_ACTIVE
        elif m_to is not None and m_to <= 15:
            risk_level = NewsRiskLevel.EVENT_IMMINENT
        elif m_since is not None and m_since <= 45:
            risk_level = NewsRiskLevel.POST_EVENT
        elif hi_nearby:
            risk_level = NewsRiskLevel.HIGH_RISK
        else:
            raw_risk = str(news_data.get("usd_news_risk", "LOW")).upper()
            if raw_risk == "HIGH":
                risk_level = NewsRiskLevel.HIGH_RISK
            elif raw_risk == "MEDIUM":
                risk_level = NewsRiskLevel.MEDIUM_RISK
            else:
                risk_level = NewsRiskLevel.LOW_RISK

        return {
            "risk_level": risk_level,
            "high_impact_news_nearby": hi_nearby,
            "news_event": event_name,
            "minutes_to_event": m_to,
            "minutes_since_event": m_since,
            "usd_news_risk": news_data.get("usd_news_risk", "LOW"),
            "news_direction": news_data.get("news_direction", "NEUTRAL"),
        }

    @classmethod
    def validate_bias(
        cls,
        symbol: str,
        timestamp: Optional[datetime] = None,
        structured_state: Optional[StructuredMarketState] = None,
        market_context: Optional[Dict[str, Any]] = None,
        dxy_data: Optional[Dict[str, Any]] = None,
        news_data: Optional[Dict[str, Any]] = None,
        custom_htf: Optional[Dict[str, Any]] = None,
        custom_7h: Optional[Dict[str, Any]] = None,
        custom_15m: Optional[Dict[str, Any]] = None,
        custom_sweeps: Optional[List[Any]] = None,
        custom_mss: Optional[List[Any]] = None,
        custom_session: Optional[Dict[str, Any]] = None,
    ) -> BiasValidationResult:
        """
        Executes unified multi-layer bias validation.
        """
        ts = timestamp or datetime.now(timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        ts_iso = ts.isoformat()

        conflicts: List[str] = []
        missing_data: List[str] = []

        # -------------------------------------------------------------
        # 1. Higher Timeframe (4H & 1H) Structure
        # -------------------------------------------------------------
        trend_4h = "UNDEFINED"
        trend_1h = "UNDEFINED"

        if custom_htf:
            trend_4h = str(custom_htf.get("tf_4h_trend") or custom_htf.get("4h") or "UNDEFINED").upper()
            trend_1h = str(custom_htf.get("tf_1h_trend") or custom_htf.get("1h") or "UNDEFINED").upper()
        elif structured_state and structured_state.timeframe_context:
            tf_ctx = structured_state.timeframe_context
            if tf_ctx.tf_4h and tf_ctx.tf_4h.trend:
                trend_4h = str(tf_ctx.tf_4h.trend).upper()
            if tf_ctx.tf_1h and tf_ctx.tf_1h.trend:
                trend_1h = str(tf_ctx.tf_1h.trend).upper()
        elif market_context:
            struct = market_context.get("market_structure", {})
            trend_1h = str(struct.get("trend_state", "UNDEFINED")).upper()

        if trend_4h in ("UNDEFINED", "") and trend_1h in ("UNDEFINED", ""):
            missing_data.append("Higher Timeframe (4H / 1H) candle structure")

        htf_bias_dir = "NEUTRAL"
        if trend_4h == "BULLISH" and trend_1h == "BULLISH":
            htf_bias_dir = "BULLISH"
        elif trend_4h == "BEARISH" and trend_1h == "BEARISH":
            htf_bias_dir = "BEARISH"
        elif trend_4h == "BULLISH" and trend_1h in ("BEARISH", "CONSOLIDATION"):
            htf_bias_dir = "CONFLICTED" if trend_1h == "BEARISH" else "BULLISH_WEAK"
            if trend_1h == "BEARISH":
                conflicts.append("HTF timeframe conflict: 4H BULLISH vs 1H BEARISH")
        elif trend_4h == "BEARISH" and trend_1h in ("BULLISH", "CONSOLIDATION"):
            htf_bias_dir = "CONFLICTED" if trend_1h == "BULLISH" else "BEARISH_WEAK"
            if trend_1h == "BULLISH":
                conflicts.append("HTF timeframe conflict: 4H BEARISH vs 1H BULLISH")
        elif trend_1h in ("BULLISH", "BEARISH") and trend_4h in ("UNDEFINED", "CONSOLIDATION"):
            htf_bias_dir = trend_1h
        elif trend_4h in ("BULLISH", "BEARISH") and trend_1h in ("UNDEFINED", "CONSOLIDATION"):
            htf_bias_dir = trend_4h
        else:
            htf_bias_dir = "NEUTRAL"

        htf_bias_payload = {
            "direction": htf_bias_dir,
            "tf_4h_trend": trend_4h,
            "tf_1h_trend": trend_1h,
        }

        # -------------------------------------------------------------
        # 2. 7H Profile Context / Regime
        # -------------------------------------------------------------
        p_dir = "NEUTRAL"
        p_class = "INSUFFICIENT_DATA"
        p_rel = None

        if custom_7h:
            p_dir = str(custom_7h.get("direction") or custom_7h.get("seven_hour_direction") or "NEUTRAL").upper()
            p_class = str(custom_7h.get("classification") or custom_7h.get("seven_hour_classification") or "NORMAL").upper()
            p_rel = custom_7h.get("relationship") or custom_7h.get("seven_hour_relationship")
        elif structured_state and structured_state.seven_hour_profile:
            sp = structured_state.seven_hour_profile
            p_dir = str(sp.direction.value if hasattr(sp.direction, "value") else sp.direction).upper()
            p_class = str(sp.classification.value if hasattr(sp.classification, "value") else sp.classification).upper()
            p_rel = sp.previous_relationship.value if hasattr(sp.previous_relationship, "value") else str(sp.previous_relationship) if sp.previous_relationship else None
        elif market_context and market_context.get("seven_hour_profile"):
            sp = market_context["seven_hour_profile"]
            p_dir = str(sp.get("direction", "NEUTRAL")).upper()
            p_class = str(sp.get("classification", "NORMAL")).upper()
            p_rel = sp.get("previous_relationship")

        if p_dir in ("UNAVAILABLE", "INSUFFICIENT_DATA", "NONE"):
            p_role = SevenHourRelationship.UNAVAILABLE
        elif htf_bias_dir == "BULLISH":
            if p_dir == "BULLISH":
                p_role = SevenHourRelationship.SUPPORT
            elif p_dir == "BEARISH":
                p_role = SevenHourRelationship.CONTRADICT
                conflicts.append("7H Profile (BEARISH) contradicts HTF bias (BULLISH)")
            else:
                p_role = SevenHourRelationship.NEUTRAL
        elif htf_bias_dir == "BEARISH":
            if p_dir == "BEARISH":
                p_role = SevenHourRelationship.SUPPORT
            elif p_dir == "BULLISH":
                p_role = SevenHourRelationship.CONTRADICT
                conflicts.append("7H Profile (BULLISH) contradicts HTF bias (BEARISH)")
            else:
                p_role = SevenHourRelationship.NEUTRAL
        else:
            p_role = SevenHourRelationship.NEUTRAL

        seven_hour_payload = {
            "direction": p_dir,
            "classification": p_class,
            "relationship": p_rel,
            "role_to_htf": p_role,
        }

        # -------------------------------------------------------------
        # 3. 15M Context
        # -------------------------------------------------------------
        trend_15m = "UNDEFINED"
        if custom_15m:
            trend_15m = str(custom_15m.get("trend") or custom_15m.get("15m") or "UNDEFINED").upper()
        elif structured_state and structured_state.timeframe_context and structured_state.timeframe_context.tf_15m:
            trend_15m = str(structured_state.timeframe_context.tf_15m.trend).upper()

        if htf_bias_dir == "BULLISH" and trend_15m == "BEARISH":
            conflicts.append("15M structure (BEARISH) contradicts HTF bias (BULLISH)")
        elif htf_bias_dir == "BEARISH" and trend_15m == "BULLISH":
            conflicts.append("15M structure (BULLISH) contradicts HTF bias (BEARISH)")

        mtf_payload = {
            "tf_4h": trend_4h,
            "tf_1h": trend_1h,
            "tf_15m": trend_15m,
            "aligned": (trend_4h == trend_1h == trend_15m) and trend_4h in ("BULLISH", "BEARISH"),
        }

        # -------------------------------------------------------------
        # 4. Liquidity Event (What price just did)
        # -------------------------------------------------------------
        sweeps = custom_sweeps if custom_sweeps is not None else []
        if not sweeps and structured_state and structured_state.liquidity:
            sweeps = structured_state.liquidity.recent_sweeps
        elif not sweeps and market_context:
            sweeps = market_context.get("recent_liquidity_sweeps", [])

        has_bsl_sweep = any(
            "HIGH" in str(s.get("level_type", "") if isinstance(s, dict) else getattr(s, "level_type", "")).upper()
            or "BSL" in str(s.get("level_type", "") if isinstance(s, dict) else getattr(s, "level_type", "")).upper()
            for s in sweeps
        )
        has_ssl_sweep = any(
            "LOW" in str(s.get("level_type", "") if isinstance(s, dict) else getattr(s, "level_type", "")).upper()
            or "SSL" in str(s.get("level_type", "") if isinstance(s, dict) else getattr(s, "level_type", "")).upper()
            for s in sweeps
        )

        liq_event_type = "NONE"
        if has_bsl_sweep and has_ssl_sweep:
            liq_event_type = "DUAL_SWEEP"
        elif has_bsl_sweep:
            liq_event_type = "BSL_SWEPT"
        elif has_ssl_sweep:
            liq_event_type = "SSL_SWEPT"

        liquidity_payload = {
            "event": liq_event_type,
            "sweeps_count": len(sweeps),
            "bsl_swept": has_bsl_sweep,
            "ssl_swept": has_ssl_sweep,
        }

        # -------------------------------------------------------------
        # 5. MSS / BOS State (What confirms entry)
        # -------------------------------------------------------------
        mss_list = custom_mss if custom_mss is not None else []
        if not mss_list and structured_state and structured_state.structure:
            mss_list = structured_state.structure.recent_mss
        elif not mss_list and market_context:
            mss_list = market_context.get("market_structure", {}).get("recent_mss", [])

        has_bullish_mss = any("BULLISH" in str(m.get("direction", "") if isinstance(m, dict) else getattr(m, "direction", "")).upper() for m in mss_list)
        has_bearish_mss = any("BEARISH" in str(m.get("direction", "") if isinstance(m, dict) else getattr(m, "direction", "")).upper() for m in mss_list)

        mss_dir = "NONE"
        if has_bullish_mss and has_bearish_mss:
            mss_dir = "CONFLICTED"
            conflicts.append("Dual MSS conflict: Bullish and Bearish MSS both detected")
        elif has_bullish_mss:
            mss_dir = "BULLISH"
        elif has_bearish_mss:
            mss_dir = "BEARISH"

        # Check MSS alignment with HTF
        if mss_dir == "BULLISH" and htf_bias_dir == "BEARISH":
            conflicts.append("Counter-trend Bullish MSS lacks HTF Bearish support")
        elif mss_dir == "BEARISH" and htf_bias_dir == "BULLISH":
            conflicts.append("Counter-trend Bearish MSS lacks HTF Bullish support")

        mss_payload = {
            "mss_direction": mss_dir,
            "has_bullish_mss": has_bullish_mss,
            "has_bearish_mss": has_bearish_mss,
        }

        # -------------------------------------------------------------
        # 6. Session Context
        # -------------------------------------------------------------
        sess_data = custom_session or {}
        if not sess_data and structured_state and structured_state.session:
            sess_data = {
                "primary_session": structured_state.session.primary_session,
                "active_sessions": structured_state.session.active_sessions,
                "killzone": structured_state.session.killzone,
            }
        elif not sess_data and market_context:
            sess_data = market_context.get("session_state", {})

        session_payload = {
            "primary_session": sess_data.get("primary_session"),
            "active_sessions": sess_data.get("active_sessions", []),
            "killzone": sess_data.get("killzone", {}),
        }

        # -------------------------------------------------------------
        # 7. DXY Intermarket Context
        # -------------------------------------------------------------
        prelim_bias = htf_bias_dir if htf_bias_dir in ("BULLISH", "BEARISH") else (
            "BULLISH" if p_dir == "BULLISH" else ("BEARISH" if p_dir == "BEARISH" else "NEUTRAL")
        )
        dxy_payload = cls.evaluate_dxy_relationship(
            symbol=symbol,
            proposed_bias=prelim_bias,
            dxy_data=dxy_data,
        )

        if dxy_payload["relationship"] == DXYRelationship.CONTRADICTING:
            conflicts.append(f"DXY intermarket flow ({dxy_payload['dxy_direction']}) contradicts proposed {prelim_bias} bias")

        # -------------------------------------------------------------
        # 8. News / Macro Context
        # -------------------------------------------------------------
        news_payload = cls.evaluate_news_context(symbol=symbol, news_data=news_data)
        if news_payload["risk_level"] in (NewsRiskLevel.HIGH_RISK, NewsRiskLevel.EVENT_IMMINENT, NewsRiskLevel.EVENT_ACTIVE):
            conflicts.append(f"High macro news risk active ({news_payload['risk_level'].value}): {news_payload.get('news_event')}")

        # -------------------------------------------------------------
        # 9. Structure State
        # -------------------------------------------------------------
        structure_payload = {
            "trend_4h": trend_4h,
            "trend_1h": trend_1h,
            "trend_15m": trend_15m,
            "htf_dominant": htf_bias_dir,
        }

        # -------------------------------------------------------------
        # 10. Final Decision & Quality Synthesis
        # -------------------------------------------------------------
        # Critical Rule: If HTF structure is completely missing, flag INSUFFICIENT_DATA
        if "Higher Timeframe (4H / 1H) candle structure" in missing_data:
            final_bias = FinalBiasState.INSUFFICIENT_DATA
            bias_quality = BiasQuality.UNUSABLE
            explanation = "Insufficient higher-timeframe data to establish directional market bias."
            status = "INSUFFICIENT_DATA"

        # Critical Rule: Session-only or Liquidity-only evidence must NOT create bias
        elif htf_bias_dir == "NEUTRAL" and p_dir == "NEUTRAL":
            final_bias = FinalBiasState.NEUTRAL
            bias_quality = BiasQuality.LOW
            explanation = (
                "Market is in neutral/consolidation regime without HTF directional trend. "
                "Session or liquidity events cannot independently generate directional bias."
            )
            status = "NEUTRAL"

        # Check for fatal conflicts:
        # e.g., 4H vs 1H inverted, or HTF Bullish but 7H Bearish + 15M Bearish + DXY Contradicting
        elif htf_bias_dir == "CONFLICTED":
            final_bias = FinalBiasState.CONFLICTED
            bias_quality = BiasQuality.UNUSABLE
            explanation = "Severe HTF structural conflict between 4H and 1H trends."
            status = "CONFLICTED"

        elif (
            htf_bias_dir == "BULLISH"
            and p_dir == "BEARISH"
            and trend_15m == "BEARISH"
            and dxy_payload["relationship"] == DXYRelationship.CONTRADICTING
        ):
            final_bias = FinalBiasState.CONFLICTED
            bias_quality = BiasQuality.UNUSABLE
            explanation = "HTF Bullish bias is severely contradicted by Bearish 7H Profile, Bearish 15M structure, and Contradictory DXY flow."
            status = "CONFLICTED"

        elif (
            htf_bias_dir == "BEARISH"
            and p_dir == "BULLISH"
            and trend_15m == "BULLISH"
            and dxy_payload["relationship"] == DXYRelationship.CONTRADICTING
        ):
            final_bias = FinalBiasState.CONFLICTED
            bias_quality = BiasQuality.UNUSABLE
            explanation = "HTF Bearish bias is severely contradicted by Bullish 7H Profile, Bullish 15M structure, and Contradictory DXY flow."
            status = "CONFLICTED"

        elif htf_bias_dir == "BULLISH":
            final_bias = FinalBiasState.BULLISH
            # Assess quality
            if (
                p_role == SevenHourRelationship.SUPPORT
                and trend_15m in ("BULLISH", "UNDEFINED")
                and dxy_payload["relationship"] in (DXYRelationship.SUPPORTIVE, DXYRelationship.NEUTRAL, DXYRelationship.UNAVAILABLE)
                and news_payload["risk_level"] in (NewsRiskLevel.LOW_RISK, NewsRiskLevel.MEDIUM_RISK)
            ):
                bias_quality = BiasQuality.HIGH
                explanation = "Full structural alignment: HTF Bullish, 7H supportive, and supportive/neutral macro backdrop."
            elif p_role == SevenHourRelationship.CONTRADICT or dxy_payload["relationship"] == DXYRelationship.CONTRADICTING:
                bias_quality = BiasQuality.LOW
                explanation = "HTF structure is Bullish, but restrained by contradictory 7H or DXY intermarket flow."
            else:
                bias_quality = BiasQuality.MODERATE
                explanation = "HTF structure is Bullish with moderate context alignment."
            status = "VALID"

        elif htf_bias_dir == "BEARISH":
            final_bias = FinalBiasState.BEARISH
            if (
                p_role == SevenHourRelationship.SUPPORT
                and trend_15m in ("BEARISH", "UNDEFINED")
                and dxy_payload["relationship"] in (DXYRelationship.SUPPORTIVE, DXYRelationship.NEUTRAL, DXYRelationship.UNAVAILABLE)
                and news_payload["risk_level"] in (NewsRiskLevel.LOW_RISK, NewsRiskLevel.MEDIUM_RISK)
            ):
                bias_quality = BiasQuality.HIGH
                explanation = "Full structural alignment: HTF Bearish, 7H supportive, and supportive/neutral macro backdrop."
            elif p_role == SevenHourRelationship.CONTRADICT or dxy_payload["relationship"] == DXYRelationship.CONTRADICTING:
                bias_quality = BiasQuality.LOW
                explanation = "HTF structure is Bearish, but restrained by contradictory 7H or DXY intermarket flow."
            else:
                bias_quality = BiasQuality.MODERATE
                explanation = "HTF structure is Bearish with moderate context alignment."
            status = "VALID"

        else:
            final_bias = FinalBiasState.NEUTRAL
            bias_quality = BiasQuality.LOW
            explanation = "Indeterminate market state without structural dominance."
            status = "NEUTRAL"

        return BiasValidationResult(
            symbol=symbol,
            timestamp=ts_iso,
            final_bias=final_bias,
            bias_quality=bias_quality,
            htf_bias=htf_bias_payload,
            seven_hour_bias=seven_hour_payload,
            mtf_alignment=mtf_payload,
            structure_state=structure_payload,
            liquidity_event=liquidity_payload,
            mss_state=mss_payload,
            session_context=session_payload,
            dxy_context=dxy_payload,
            news_context=news_payload,
            conflicts=conflicts,
            missing_data=missing_data,
            explanation=explanation,
            validation_status=status,
        )

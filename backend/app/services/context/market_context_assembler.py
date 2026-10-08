from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from app.schemas.candle import CandleRead
from app.schemas.seven_hour_profile import (
    SevenHourProfileResult,
    SevenHourProfileConfig,
    ProfileClassification,
    ProfileDirection,
    ProfileStatus,
    DataQuality,
)
from app.schemas.market_state import (
    StructuredMarketState,
    SevenHourProfileContext,
    SessionContext,
    TimeframeContext,
    TimeframeSummary,
    StructureContext,
    LiquidityContext,
    ProfileSessionInteraction,
    HistoricalProfileContext,
)
from app.services.features.indicators import TechnicalIndicators
from app.services.features.structure import LiquiditySweep
from app.services.features.context_engine import MarketStructureSnapshot
from app.services.features.reference_levels import KeyReferenceLevels
from app.services.session.session_engine import SessionEngine, CurrentSessionState
from app.services.profiling.seven_hour_profile_engine import SevenHourProfileEngine


class MarketContextAssembler:
    """
    Higher-Level Multi-Layer Context Assembler.
    
    Coordinates independent analytical engines:
    - 7H Profile Engine: Synthetic HTF profile/regime classification
    - Session Engine: Real-world institutional market sessions & killzones
    - Market Structure Analyzer: Swings, displacement, MSS, FVGs
    - Reference Levels & Liquidity: Key pools (BSL/SSL) and sweeps
    - Multi-timeframe timeseries hierarchy (4h, 1h, 15m, requested)
    
    CRITICAL ARCHITECTURAL CONSTRAINTS:
    - 7H Profile Engine and SessionEngine remain strictly independent.
    - Zero trade setups, signals, or execution directives are generated here.
    - All cross-layer interactions are purely factual and non-prescriptive.
    """

    @classmethod
    def build_timeframe_summary(
        cls, timeframe: str, candles: List[CandleRead]
    ) -> TimeframeSummary:
        """Computes summary metrics for a single timeframe."""
        if not candles:
            return TimeframeSummary(timeframe=timeframe, candle_count=0)

        closes = [float(c.close) for c in candles]
        highs = [float(c.high) for c in candles]
        lows = [float(c.low) for c in candles]
        last_c = candles[-1]

        # Calculate lightweight indicators if enough bars exist
        rsi_val = None
        if len(closes) >= 15:
            rsi_series = TechnicalIndicators.calculate_rsi(closes, 14)
            rsi_val = rsi_series[-1]

        atr_val = None
        if len(closes) >= 15:
            atr_series = TechnicalIndicators.calculate_atr(highs, lows, closes, 14)
            atr_val = atr_series[-1]

        ema_21_val = None
        if len(closes) >= 21:
            ema_21_val = TechnicalIndicators.calculate_ema(closes, 21)[-1]

        ema_50_val = None
        if len(closes) >= 50:
            ema_50_val = TechnicalIndicators.calculate_ema(closes, 50)[-1]

        # Lightweight trend heuristic
        trend = "UNDEFINED"
        if ema_21_val is not None:
            if last_c.close > ema_21_val:
                trend = "BULLISH"
            elif last_c.close < ema_21_val:
                trend = "BEARISH"

        return TimeframeSummary(
            timeframe=timeframe,
            candle_count=len(candles),
            last_candle_timestamp=last_c.timestamp_utc,
            current_price=float(last_c.close),
            trend=trend,
            rsi_14=rsi_val,
            atr_14=atr_val,
            ema_21=ema_21_val,
            ema_50=ema_50_val,
        )

    @classmethod
    def build_timeframe_context(
        cls,
        requested_timeframe: str,
        candles_by_timeframe: Dict[str, List[CandleRead]],
    ) -> TimeframeContext:
        """Builds multi-timeframe hierarchy context."""
        c_4h = candles_by_timeframe.get("4h", [])
        c_1h = candles_by_timeframe.get("1h", [])
        c_15m = candles_by_timeframe.get("15m", [])
        c_req = candles_by_timeframe.get(requested_timeframe, [])

        return TimeframeContext(
            tf_4h=cls.build_timeframe_summary("4h", c_4h) if c_4h else None,
            tf_1h=cls.build_timeframe_summary("1h", c_1h) if c_1h else None,
            tf_15m=cls.build_timeframe_summary("15m", c_15m) if c_15m else None,
            requested_timeframe=requested_timeframe,
            requested=cls.build_timeframe_summary(requested_timeframe, c_req) if c_req else None,
        )

    @classmethod
    def build_seven_hour_context(
        cls, profile: Optional[SevenHourProfileResult]
    ) -> SevenHourProfileContext:
        """Adapts SevenHourProfileResult to SevenHourProfileContext with safe defaults."""
        if profile is None:
            return SevenHourProfileContext(
                classification=ProfileClassification.INSUFFICIENT_DATA,
                direction=ProfileDirection.NEUTRAL,
                range=0.0,
                normalized_range=None,
                previous_relationship=None,
                status=ProfileStatus.IN_PROGRESS,
                data_quality=DataQuality.INSUFFICIENT,
            )

        return SevenHourProfileContext(
            classification=profile.classification,
            direction=profile.direction,
            range=profile.range,
            normalized_range=profile.features.normalized_range,
            previous_relationship=profile.relationship,
            status=profile.status,
            data_quality=profile.data_quality,
            profile_start=profile.profile_start,
            profile_end=profile.profile_end,
            source_candle_count=profile.source_candle_count,
            config_id=profile.config_id,
        )

    @classmethod
    def build_session_context(
        cls,
        session_state: Optional[CurrentSessionState],
        dt_utc: datetime,
    ) -> SessionContext:
        """Adapts CurrentSessionState to SessionContext with institutional killzone resolution."""
        kz = SessionEngine.get_killzone_info(dt_utc)

        if session_state is None:
            return SessionContext(
                active_sessions=[],
                primary_session=None,
                overlap=False,
                overlap_name=None,
                killzone=kz,
                session_levels={},
            )

        return SessionContext(
            active_sessions=session_state.active_sessions,
            primary_session=session_state.primary_session,
            overlap=session_state.is_overlap,
            overlap_name=session_state.overlap_name,
            killzone=kz,
            session_levels=session_state.session_levels,
        )

    @classmethod
    def build_structure_context(
        cls, structure: Optional[MarketStructureSnapshot]
    ) -> StructureContext:
        """Extracts trend state, recent MSS, and swing points."""
        if structure is None:
            return StructureContext(trend="UNDEFINED", recent_mss=[], recent_bos=[], swings=[])

        mss_list = [m.model_dump() if hasattr(m, "model_dump") else dict(m) for m in structure.recent_mss]
        swings_list = [s.model_dump() if hasattr(s, "model_dump") else dict(s) for s in structure.recent_swings]

        return StructureContext(
            trend=structure.trend_state,
            recent_mss=mss_list,
            recent_bos=[],
            swings=swings_list,
        )

    @classmethod
    def build_liquidity_context(
        cls,
        reference_levels: Optional[KeyReferenceLevels],
        sweeps: Optional[List[Any]],
    ) -> LiquidityContext:
        """Builds Buy-Side / Sell-Side Liquidity references and recent confirmed sweeps."""
        bsl = reference_levels.previous_day_high if reference_levels else None
        ssl = reference_levels.previous_day_low if reference_levels else None

        sweeps_data: List[Dict[str, Any]] = []
        if sweeps:
            for s in sweeps:
                if hasattr(s, "model_dump"):
                    sweeps_data.append(s.model_dump())
                elif isinstance(s, dict):
                    sweeps_data.append(s)

        return LiquidityContext(
            bsl=bsl,
            ssl=ssl,
            recent_sweeps=sweeps_data,
        )

    @classmethod
    def build_profile_session_interaction(
        cls,
        seven_hour_profile: Optional[SevenHourProfileResult],
        session_context: SessionContext,
        sweeps: Optional[List[Any]],
    ) -> ProfileSessionInteraction:
        """
        Determines cross-layer interaction between 7H profile and market session.
        Strictly factual, descriptive, and non-prescriptive (no trade bias).
        """
        p_dir = seven_hour_profile.direction if seven_hour_profile else None
        curr_session = session_context.primary_session
        kz = session_context.killzone or {}

        recent_event = "NONE"
        if sweeps:
            # Check latest sweep for session level interaction
            last_sweep = sweeps[-1]
            l_type = ""
            if hasattr(last_sweep, "level_type"):
                l_type = str(last_sweep.level_type).upper()
            elif isinstance(last_sweep, dict):
                l_type = str(last_sweep.get("level_type", "")).upper()

            if "HIGH" in l_type:
                recent_event = "BSL_SWEEP"
            elif "LOW" in l_type:
                recent_event = "SSL_SWEEP"

        notes = (
            f"Profile direction: {p_dir.value if p_dir else 'UNKNOWN'}; "
            f"Active session: {curr_session or 'OFF_SESSION'}; "
            f"Killzone: {kz.get('name', 'None')}; "
            f"Recent liquidity event: {recent_event}"
        )

        return ProfileSessionInteraction(
            profile_direction=p_dir,
            active_session=curr_session,
            killzone_active=kz.get("is_killzone", False),
            killzone_name=kz.get("name"),
            recent_session_event=recent_event,
            notes=notes,
        )

    @classmethod
    def assemble(
        cls,
        symbol: str,
        requested_timeframe: str,
        current_candle: CandleRead,
        candles_by_timeframe: Dict[str, List[CandleRead]],
        seven_hour_profile: Optional[SevenHourProfileResult] = None,
        session_state: Optional[CurrentSessionState] = None,
        market_structure: Optional[MarketStructureSnapshot] = None,
        reference_levels: Optional[KeyReferenceLevels] = None,
        recent_liquidity_sweeps: Optional[List[Any]] = None,
        historical_profile_context: Optional[HistoricalProfileContext] = None,
        seven_hour_config: Optional[SevenHourProfileConfig] = None,
    ) -> StructuredMarketState:
        """
        Synthesizes the complete multi-layer StructuredMarketState object.
        Preserves complete independence between 7H Profile and Session Engine.
        """
        ts_utc = current_candle.timestamp_utc
        if ts_utc.tzinfo is None:
            ts_utc = ts_utc.replace(tzinfo=timezone.utc)
        else:
            ts_utc = ts_utc.astimezone(timezone.utc)

        current_price = float(current_candle.close)

        # 1. 7H Profile: use provided or synthesize from 1h / lower candles if available
        profile_res = seven_hour_profile
        if profile_res is None:
            # Check if 1h candles or requested candles exist for 7H evaluation
            c_for_7h = candles_by_timeframe.get("1h") or candles_by_timeframe.get(requested_timeframe) or []
            if c_for_7h:
                cfg = seven_hour_config or SevenHourProfileConfig(source_timeframe=c_for_7h[0].timeframe)
                profiles = SevenHourProfileEngine.evaluate_candles(
                    symbol=symbol,
                    candles=c_for_7h,
                    config=cfg,
                    current_time_utc=ts_utc,
                )
                if profiles:
                    profile_res = profiles[-1]

        p_context = cls.build_seven_hour_context(profile_res)

        # 2. Session Context: use provided or evaluate at timestamp
        sess_state = session_state
        if sess_state is None:
            sess_candles = candles_by_timeframe.get(requested_timeframe) or []
            sess_state = SessionEngine.evaluate_sessions(
                dt_utc=ts_utc,
                candles_today=sess_candles,
                current_candle=current_candle,
            )
        s_context = cls.build_session_context(sess_state, ts_utc)

        # 3. Multi-Timeframe Context
        tf_context = cls.build_timeframe_context(requested_timeframe, candles_by_timeframe)

        # 4. Structure Context
        struct_context = cls.build_structure_context(market_structure)

        # 5. Liquidity Context
        liq_context = cls.build_liquidity_context(reference_levels, recent_liquidity_sweeps)

        # 6. Profile vs Session Cross-Layer Interaction (Objective / Non-Prescriptive)
        interaction = cls.build_profile_session_interaction(
            seven_hour_profile=profile_res,
            session_context=s_context,
            sweeps=recent_liquidity_sweeps,
        )

        return StructuredMarketState(
            symbol=symbol,
            timestamp_utc=ts_utc,
            current_price=current_price,
            seven_hour_profile=p_context,
            session=s_context,
            timeframe_context=tf_context,
            structure=struct_context,
            liquidity=liq_context,
            profile_vs_session_interaction=interaction,
            historical_profile_context=historical_profile_context,
        )

    @classmethod
    def build_dxy_context(
        cls,
        symbol: str,
        direction: str,
        dxy_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Builds DXY intermarket conditioning context.
        Relationship:
        - For USD quote (EURUSD, GBPUSD, XAUUSD, XAGUSD):
            DXY BULLISH => USD stronger => quote drops. BUY is CONTRADICTING, SELL is SUPPORTIVE.
            DXY BEARISH => USD weaker => quote rises. BUY is SUPPORTIVE, SELL is CONTRADICTING.
        - For USD base (USDJPY, USDCAD, USDCHF):
            DXY BULLISH => USD stronger => base rises. BUY is SUPPORTIVE, SELL is CONTRADICTING.
            DXY BEARISH => USD weaker => base drops. BUY is CONTRADICTING, SELL is SUPPORTIVE.
        """
        if not dxy_data:
            return {
                "dxy_direction": "UNAVAILABLE",
                "dxy_trend_strength": None,
                "dxy_change": None,
                "dxy_relationship_to_symbol": "UNAVAILABLE",
            }

        dxy_dir = dxy_data.get("direction") or dxy_data.get("trend") or "NEUTRAL"
        strength = dxy_data.get("trend_strength")
        change = dxy_data.get("change") or dxy_data.get("change_pct")

        sym_upper = symbol.upper()
        is_usd_quote = any(sym_upper.startswith(prefix) for prefix in ["EUR", "GBP", "AUD", "NZD", "XAU", "XAG"])
        is_usd_base = sym_upper.startswith("USD")

        is_buy = "BUY" in direction.upper() or "LONG" in direction.upper()

        if dxy_dir == "NEUTRAL":
            rel = "NEUTRAL"
        elif is_usd_quote:
            if dxy_dir == "BULLISH":
                rel = "CONTRADICTING" if is_buy else "SUPPORTIVE"
            else:  # BEARISH
                rel = "SUPPORTIVE" if is_buy else "CONTRADICTING"
        elif is_usd_base:
            if dxy_dir == "BULLISH":
                rel = "SUPPORTIVE" if is_buy else "CONTRADICTING"
            else:
                rel = "CONTRADICTING" if is_buy else "SUPPORTIVE"
        else:
            rel = "NEUTRAL"

        return {
            "dxy_direction": dxy_dir,
            "dxy_trend_strength": strength,
            "dxy_change": change,
            "dxy_relationship_to_symbol": rel,
        }

    _build_dxy_context = build_dxy_context

    @classmethod
    def build_news_context(
        cls,
        symbol: str,
        news_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Builds News intelligence conditioning context.
        """
        if not news_data:
            return {
                "high_impact_news_nearby": False,
                "news_direction": "UNAVAILABLE",
                "news_event": None,
                "minutes_to_event": None,
                "minutes_since_event": None,
                "usd_news_risk": "UNAVAILABLE",
            }

        return {
            "high_impact_news_nearby": bool(news_data.get("high_impact_news_nearby", False)),
            "news_direction": news_data.get("news_direction", "NEUTRAL"),
            "news_event": news_data.get("news_event"),
            "minutes_to_event": news_data.get("minutes_to_event"),
            "minutes_since_event": news_data.get("minutes_since_event"),
            "usd_news_risk": news_data.get("usd_news_risk", "LOW"),
        }

    _build_news_context = build_news_context

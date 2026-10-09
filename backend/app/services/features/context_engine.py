from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict

from app.schemas.candle import CandleRead
from app.services.features.indicators import TechnicalIndicators
from app.services.features.structure import (
    MarketStructureAnalyzer, SwingPoint, FairValueGap, LiquiditySweep, CandleStructure, MarketStructureShift
)
from app.services.features.reference_levels import ReferenceLevelsCalculator, KeyReferenceLevels
from app.services.session import SessionEngine, CurrentSessionState
from app.schemas.market_state import StructuredMarketState

class TechnicalIndicatorsSnapshot(BaseModel):
    rsi_14: Optional[float] = None
    atr_14: Optional[float] = None
    atr_14_pips: Optional[float] = None
    ema_9: Optional[float] = None
    ema_21: Optional[float] = None
    ema_50: Optional[float] = None
    ema_200: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_hist: Optional[float] = None
    adx: Optional[float] = None
    plus_di: Optional[float] = None
    minus_di: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)

class MarketStructureSnapshot(BaseModel):
    recent_swings: List[SwingPoint] = []
    active_unmitigated_fvgs: List[FairValueGap] = []
    recent_mss: List[MarketStructureShift] = []
    trend_state: str = "UNDEFINED"  # "BULLISH", "BEARISH", "CONSOLIDATION"

class MarketContextSnapshot(BaseModel):
    """
    Comprehensive, objective market state snapshot provided to the AI Engine.
    Exposes all requested features without any hardcoded trading bias.
    """
    symbol: str
    timeframe: str
    timestamp_utc: datetime
    current_price: float
    current_candle: CandleRead
    candle_structure: CandleStructure
    indicators: TechnicalIndicatorsSnapshot
    market_structure: MarketStructureSnapshot
    reference_levels: KeyReferenceLevels
    session_state: Optional[CurrentSessionState] = None
    recent_liquidity_sweeps: List[LiquiditySweep] = []
    structured_market_state: Optional[StructuredMarketState] = None
    dxy: Optional[Dict[str, Any]] = None
    news: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

class MarketContextEngine:
    """
    Assembles a complete, institutional market context snapshot
    from raw OHLCV timeseries bars.
    """

    @classmethod
    def generate_context(
        cls,
        symbol: str,
        timeframe: str,
        candles: List[CandleRead],
        daily_candles: Optional[List[CandleRead]] = None,
        pip_size: float = 0.0001,
    ) -> MarketContextSnapshot:
        if not candles:
            raise ValueError("At least one candle is required to generate market context.")

        current_candle = candles[-1]
        closes = [c.close for c in candles]
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]

        # 1. Technical Indicators
        ema_9 = TechnicalIndicators.calculate_ema(closes, 9)[-1]
        ema_21 = TechnicalIndicators.calculate_ema(closes, 21)[-1]
        ema_50 = TechnicalIndicators.calculate_ema(closes, 50)[-1]
        ema_200 = TechnicalIndicators.calculate_ema(closes, 200)[-1]

        rsi_14 = TechnicalIndicators.calculate_rsi(closes, 14)[-1]
        atr_14 = TechnicalIndicators.calculate_atr(highs, lows, closes, 14)[-1]
        atr_pips = round(atr_14 / pip_size, 1) if atr_14 is not None else None

        macd_data = TechnicalIndicators.calculate_macd(closes, 12, 26, 9)
        macd_val = macd_data["macd"][-1]
        macd_sig = macd_data["signal"][-1]
        macd_hist = macd_data["histogram"][-1]

        adx_data = TechnicalIndicators.calculate_adx(highs, lows, closes, 14)
        adx_val = adx_data["adx"][-1]
        plus_di = adx_data["plus_di"][-1]
        minus_di = adx_data["minus_di"][-1]

        ind_snapshot = TechnicalIndicatorsSnapshot(
            rsi_14=rsi_14,
            atr_14=atr_14,
            atr_14_pips=atr_pips,
            ema_9=ema_9,
            ema_21=ema_21,
            ema_50=ema_50,
            ema_200=ema_200,
            macd=macd_val,
            macd_signal=macd_sig,
            macd_hist=macd_hist,
            adx=adx_val,
            plus_di=plus_di,
            minus_di=minus_di,
        )

        # 2. Candle Structure
        prev_candle = candles[-2] if len(candles) >= 2 else None
        candle_struct = MarketStructureAnalyzer.analyze_candle_structure(
            candle=current_candle,
            previous_candle=prev_candle,
            pip_size=pip_size
        )

        # 3. Market Structure (Swings, FVGs, Trend State)
        swings = MarketStructureAnalyzer.identify_swings(candles, left_bars=2, right_bars=2)
        recent_swings = swings[-6:] if len(swings) >= 6 else swings

        # Trend state from recent swing labels
        trend_state = "CONSOLIDATION"
        if len(recent_swings) >= 2:
            high_swings = [s for s in recent_swings if s.point_type == "HIGH"]
            low_swings = [s for s in recent_swings if s.point_type == "LOW"]
            if high_swings and low_swings:
                if high_swings[-1].label == "HH" and low_swings[-1].label == "HL":
                    trend_state = "BULLISH"
                elif high_swings[-1].label == "LH" and low_swings[-1].label == "LL":
                    trend_state = "BEARISH"

        fvgs = MarketStructureAnalyzer.detect_fair_value_gaps(candles, pip_size=pip_size)
        active_fvgs = [f for f in fvgs if not f.mitigated][-5:]

        recent_mss = MarketStructureAnalyzer.detect_market_structure_shift(
            candles=candles,
            recent_swings=recent_swings,
            pip_size=pip_size,
            lookback=15,
        )

        struct_snapshot = MarketStructureSnapshot(
            recent_swings=recent_swings,
            active_unmitigated_fvgs=active_fvgs,
            recent_mss=recent_mss,
            trend_state=trend_state,
        )

        # 4. Reference Levels (PDH/PDL, PWH/PWL, ADR)
        daily_bars = daily_candles or []
        ref_levels = ReferenceLevelsCalculator.calculate_levels(
            daily_candles=daily_bars,
            current_candle=current_candle,
            pip_size=pip_size
        )

        # 5. Session State & Session Levels
        session_state = SessionEngine.evaluate_sessions(
            dt_utc=current_candle.timestamp_utc,
            candles_today=candles,
            pip_size=pip_size,
            current_candle=current_candle,
        )

        # 6. Liquidity Sweeps (scanning last 10 candles for confirmed sweeps)
        sweeps: List[LiquiditySweep] = []
        if recent_swings:
            recent_high = max([s.price for s in recent_swings if s.point_type == "HIGH"], default=None)
            recent_low = min([s.price for s in recent_swings if s.point_type == "LOW"], default=None)
            swing_sweeps = MarketStructureAnalyzer.detect_recent_sweeps(
                candles=candles,
                reference_high=recent_high,
                reference_low=recent_low,
                lookback=10,
                pip_size=pip_size,
                level_label_prefix="SWING",
            )
            sweeps.extend(swing_sweeps)

        # Check sweep against PDH / PDL
        if ref_levels.previous_day_high is not None or ref_levels.previous_day_low is not None:
            pd_sweeps = MarketStructureAnalyzer.detect_recent_sweeps(
                candles=candles,
                reference_high=ref_levels.previous_day_high,
                reference_low=ref_levels.previous_day_low,
                lookback=10,
                pip_size=pip_size,
                level_label_prefix="PD",
            )
            sweeps.extend(pd_sweeps)

        # Check sweep against Session Levels (Asian High/Low, London High/Low, etc.)
        for s_name, s_lvl in session_state.session_levels.items():
            if s_lvl.high is not None or s_lvl.low is not None:
                sess_sweeps = MarketStructureAnalyzer.detect_recent_sweeps(
                    candles=candles,
                    reference_high=s_lvl.high,
                    reference_low=s_lvl.low,
                    lookback=10,
                    pip_size=pip_size,
                    level_label_prefix=s_name.upper(),
                )
                sweeps.extend(sess_sweeps)

        return MarketContextSnapshot(
            symbol=symbol,
            timeframe=timeframe,
            timestamp_utc=current_candle.timestamp_utc,
            current_price=current_candle.close,
            current_candle=current_candle,
            candle_structure=candle_struct,
            indicators=ind_snapshot,
            market_structure=struct_snapshot,
            reference_levels=ref_levels,
            session_state=session_state,
            recent_liquidity_sweeps=sweeps,
        )

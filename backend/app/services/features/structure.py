from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.candle import CandleRead

class SwingPoint(BaseModel):
    point_type: str  # "HIGH" or "LOW"
    price: float
    timestamp_utc: datetime
    index: int
    label: Optional[str] = None  # "HH", "LH", "HL", "LL"

    model_config = ConfigDict(from_attributes=True)

class FairValueGap(BaseModel):
    fvg_type: str  # "BULLISH" or "BEARISH"
    top_price: float
    bottom_price: float
    gap_size_pips: float
    formed_at_utc: datetime
    mitigated: bool = False
    mitigated_at_utc: Optional[datetime] = None

class LiquiditySweep(BaseModel):
    level_type: str  # "SWING_HIGH", "SWING_LOW", "SESSION_HIGH", "SESSION_LOW", "PDH", "PDL"
    level_price: float
    sweep_candle_ts: datetime
    extreme_price: float
    sweep_depth_pips: float
    closed_inside: bool
    rejection_wick_ratio: float = 0.0
    is_exhaustion_candle: bool = False

    model_config = ConfigDict(from_attributes=True)

class MarketStructureShift(BaseModel):
    mss_type: str  # "BULLISH" or "BEARISH"
    broken_swing_price: float
    shift_candle_ts: datetime
    candles_ago: int
    has_fvg: bool = False
    displacement_pips: float = 0.0

    model_config = ConfigDict(from_attributes=True)

class CandleStructure(BaseModel):
    direction: str  # "BULLISH", "BEARISH", "NEUTRAL"
    body_pips: float
    upper_wick_pips: float
    lower_wick_pips: float
    is_pin_bar: bool
    is_engulfing: bool

    model_config = ConfigDict(from_attributes=True)

class MarketStructureAnalyzer:
    """
    Computes market structure, liquidity zones, and price action metrics
    purely as objective data without asserting trade strategy.
    """

    @staticmethod
    def identify_swings(
        candles: List[CandleRead], left_bars: int = 2, right_bars: int = 2
    ) -> List[SwingPoint]:
        """
        Identifies fractal swing highs and swing lows using an N-bar window.
        A bar is a swing high if its high is strictly greater than left_bars and right_bars.
        """
        n = len(candles)
        swings: List[SwingPoint] = []
        if n < left_bars + right_bars + 1:
            return swings

        for i in range(left_bars, n - right_bars):
            curr_h = candles[i].high
            curr_l = candles[i].low

            # Check Swing High
            is_high = True
            for offset in range(-left_bars, right_bars + 1):
                if offset != 0 and candles[i + offset].high >= curr_h:
                    is_high = False
                    break
            if is_high:
                swings.append(
                    SwingPoint(
                        point_type="HIGH",
                        price=curr_h,
                        timestamp_utc=candles[i].timestamp_utc,
                        index=i
                    )
                )

            # Check Swing Low
            is_low = True
            for offset in range(-left_bars, right_bars + 1):
                if offset != 0 and candles[i + offset].low <= curr_l:
                    is_low = False
                    break
            if is_low:
                swings.append(
                    SwingPoint(
                        point_type="LOW",
                        price=curr_l,
                        timestamp_utc=candles[i].timestamp_utc,
                        index=i
                    )
                )

        # Label sequential swing points (HH, LH, HL, LL)
        last_high: Optional[float] = None
        last_low: Optional[float] = None

        for sp in swings:
            if sp.point_type == "HIGH":
                if last_high is not None:
                    sp.label = "HH" if sp.price > last_high else "LH"
                last_high = sp.price
            elif sp.point_type == "LOW":
                if last_low is not None:
                    sp.label = "HL" if sp.price > last_low else "LL"
                last_low = sp.price

        return swings

    @staticmethod
    def detect_fair_value_gaps(
        candles: List[CandleRead], pip_size: float = 0.0001
    ) -> List[FairValueGap]:
        """
        Detects 3-bar Fair Value Gaps (FVG / Imbalances):
        - Bullish: Candle[i-2].high < Candle[i].low (gap between bar 1 high and bar 3 low)
        - Bearish: Candle[i-2].low > Candle[i].high (gap between bar 1 low and bar 3 high)
        """
        fvgs: List[FairValueGap] = []
        n = len(candles)
        if n < 3:
            return fvgs

        for i in range(2, n):
            c1 = candles[i - 2]
            c3 = candles[i]

            # Bullish FVG
            if c3.low > c1.high:
                gap_size = round((c3.low - c1.high) / pip_size, 1)
                fvg = FairValueGap(
                    fvg_type="BULLISH",
                    top_price=c3.low,
                    bottom_price=c1.high,
                    gap_size_pips=gap_size,
                    formed_at_utc=c3.timestamp_utc,
                    mitigated=False
                )
                # Check subsequent bars for mitigation
                for k in range(i + 1, n):
                    if candles[k].low <= fvg.bottom_price:
                        fvg.mitigated = True
                        fvg.mitigated_at_utc = candles[k].timestamp_utc
                        break
                fvgs.append(fvg)

            # Bearish FVG
            elif c3.high < c1.low:
                gap_size = round((c1.low - c3.high) / pip_size, 1)
                fvg = FairValueGap(
                    fvg_type="BEARISH",
                    top_price=c1.low,
                    bottom_price=c3.high,
                    gap_size_pips=gap_size,
                    formed_at_utc=c3.timestamp_utc,
                    mitigated=False
                )
                for k in range(i + 1, n):
                    if candles[k].high >= fvg.top_price:
                        fvg.mitigated = True
                        fvg.mitigated_at_utc = candles[k].timestamp_utc
                        break
                fvgs.append(fvg)

        return fvgs

    @staticmethod
    def detect_liquidity_sweep(
        current_candle: CandleRead,
        reference_high: Optional[float],
        reference_low: Optional[float],
        pip_size: float = 0.0001,
        level_label_prefix: str = "KEY"
    ) -> List[LiquiditySweep]:
        """
        Detects if current candle has breached a key level by wick and closed inside.
        """
        sweeps: List[LiquiditySweep] = []

        # Sweep of High: High > reference_high, but Close <= reference_high
        if reference_high is not None and current_candle.high > reference_high:
            closed_inside = current_candle.close <= reference_high
            depth_pips = round((current_candle.high - reference_high) / pip_size, 1)
            sweeps.append(
                LiquiditySweep(
                    level_type=f"{level_label_prefix}_HIGH",
                    level_price=reference_high,
                    sweep_candle_ts=current_candle.timestamp_utc,
                    extreme_price=current_candle.high,
                    sweep_depth_pips=depth_pips,
                    closed_inside=closed_inside
                )
            )

        # Sweep of Low: Low < reference_low, but Close >= reference_low
        if reference_low is not None and current_candle.low < reference_low:
            closed_inside = current_candle.close >= reference_low
            depth_pips = round((reference_low - current_candle.low) / pip_size, 1)
            sweeps.append(
                LiquiditySweep(
                    level_type=f"{level_label_prefix}_LOW",
                    level_price=reference_low,
                    sweep_candle_ts=current_candle.timestamp_utc,
                    extreme_price=current_candle.low,
                    sweep_depth_pips=depth_pips,
                    closed_inside=closed_inside
                )
            )

        return sweeps

    @staticmethod
    def detect_recent_sweeps(
        candles: List[CandleRead],
        reference_high: Optional[float],
        reference_low: Optional[float],
        lookback: int = 10,
        pip_size: float = 0.0001,
        level_label_prefix: str = "KEY",
    ) -> List[LiquiditySweep]:
        """
        Scans across recent lookback candles to detect any recent liquidity sweep
        where a candle wicked through reference_high or reference_low and closed inside.
        """
        sweeps: List[LiquiditySweep] = []
        if not candles:
            return sweeps

        window = candles[-lookback:]
        for candle in window:
            c_range = candle.high - candle.low
            if reference_high is not None and candle.high > reference_high:
                if candle.close <= reference_high:
                    depth_pips = round((candle.high - reference_high) / pip_size, 1)
                    upper_wick = candle.high - max(candle.open, candle.close)
                    wick_ratio = round(upper_wick / c_range, 2) if c_range > 0 else 0.0
                    sweeps.append(
                        LiquiditySweep(
                            level_type=f"{level_label_prefix}_HIGH",
                            level_price=reference_high,
                            sweep_candle_ts=candle.timestamp_utc,
                            extreme_price=candle.high,
                            sweep_depth_pips=depth_pips,
                            closed_inside=True,
                            rejection_wick_ratio=wick_ratio,
                            is_exhaustion_candle=(wick_ratio >= 0.35),
                        )
                    )
            if reference_low is not None and candle.low < reference_low:
                if candle.close >= reference_low:
                    depth_pips = round((reference_low - candle.low) / pip_size, 1)
                    lower_wick = min(candle.open, candle.close) - candle.low
                    wick_ratio = round(lower_wick / c_range, 2) if c_range > 0 else 0.0
                    sweeps.append(
                        LiquiditySweep(
                            level_type=f"{level_label_prefix}_LOW",
                            level_price=reference_low,
                            sweep_candle_ts=candle.timestamp_utc,
                            extreme_price=candle.low,
                            sweep_depth_pips=depth_pips,
                            closed_inside=True,
                            rejection_wick_ratio=wick_ratio,
                            is_exhaustion_candle=(wick_ratio >= 0.35),
                        )
                    )
        return sweeps

    @staticmethod
    def detect_market_structure_shift(
        candles: List[CandleRead],
        recent_swings: List[SwingPoint],
        pip_size: float = 0.0001,
        lookback: int = 12,
    ) -> List[MarketStructureShift]:
        """
        Detects Market Structure Shifts (MSS) where recent candle closes break through
        opposing fractal swing points with displacement.
        """
        shifts: List[MarketStructureShift] = []
        if len(candles) < 3 or not recent_swings:
            return shifts

        n = len(candles)
        window_start = max(0, n - lookback)

        low_swings = [s for s in recent_swings if s.point_type == "LOW"]
        high_swings = [s for s in recent_swings if s.point_type == "HIGH"]

        # Bearish MSS: Price closes below the most recent key swing low
        if low_swings:
            target_low = low_swings[-1]
            for i in range(window_start, n):
                c = candles[i]
                if c.timestamp_utc > target_low.timestamp_utc and c.close < target_low.price:
                    disp = round((target_low.price - c.close) / pip_size, 1)
                    shifts.append(
                        MarketStructureShift(
                            mss_type="BEARISH",
                            broken_swing_price=target_low.price,
                            shift_candle_ts=c.timestamp_utc,
                            candles_ago=n - 1 - i,
                            has_fvg=False,
                            displacement_pips=disp,
                        )
                    )
                    break

        # Bullish MSS: Price closes above the most recent key swing high
        if high_swings:
            target_high = high_swings[-1]
            for i in range(window_start, n):
                c = candles[i]
                if c.timestamp_utc > target_high.timestamp_utc and c.close > target_high.price:
                    disp = round((c.close - target_high.price) / pip_size, 1)
                    shifts.append(
                        MarketStructureShift(
                            mss_type="BULLISH",
                            broken_swing_price=target_high.price,
                            shift_candle_ts=c.timestamp_utc,
                            candles_ago=n - 1 - i,
                            has_fvg=False,
                            displacement_pips=disp,
                        )
                    )
                    break

        return shifts

    @staticmethod
    def analyze_candle_structure(
        candle: CandleRead,
        previous_candle: Optional[CandleRead] = None,
        pip_size: float = 0.0001
    ) -> CandleStructure:
        """
        Calculates body, upper wick, and lower wick sizes in pips,
        and identifies pin bars and engulfing patterns.
        """
        body_top = max(candle.open, candle.close)
        body_bottom = min(candle.open, candle.close)

        body_pips = round((body_top - body_bottom) / pip_size, 1)
        upper_wick_pips = round((candle.high - body_top) / pip_size, 1)
        lower_wick_pips = round((body_bottom - candle.low) / pip_size, 1)

        total_range = candle.high - candle.low
        is_pin = False
        if total_range > 0:
            # Pin bar if wick >= 60% of total range and body <= 25% of range
            if (upper_wick_pips * pip_size >= total_range * 0.60) or (lower_wick_pips * pip_size >= total_range * 0.60):
                if body_pips * pip_size <= total_range * 0.30:
                    is_pin = True

        # Direction
        if candle.close > candle.open:
            direction = "BULLISH"
        elif candle.close < candle.open:
            direction = "BEARISH"
        else:
            direction = "NEUTRAL"

        # Engulfing check
        is_engulfing = False
        if previous_candle is not None:
            prev_body_top = max(previous_candle.open, previous_candle.close)
            prev_body_bottom = min(previous_candle.open, previous_candle.close)
            if body_top > prev_body_top and body_bottom < prev_body_bottom:
                is_engulfing = True

        return CandleStructure(
            direction=direction,
            body_pips=body_pips,
            upper_wick_pips=upper_wick_pips,
            lower_wick_pips=lower_wick_pips,
            is_pin_bar=is_pin,
            is_engulfing=is_engulfing
        )

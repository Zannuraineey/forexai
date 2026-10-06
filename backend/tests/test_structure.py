import pytest
from datetime import datetime, timezone, timedelta
from app.schemas.candle import CandleRead
from app.services.features.structure import MarketStructureAnalyzer

def make_candle(idx: int, o: float, h: float, l: float, c: float) -> CandleRead:
    return CandleRead(
        id=idx,
        instrument_id=1,
        timeframe="15m",
        timestamp_utc=datetime(2026, 10, 4, 10, 0, 0, tzinfo=timezone.utc) + timedelta(minutes=15 * idx),
        open=o,
        high=h,
        low=l,
        close=c,
        volume=100.0,
        provider="mock",
        is_complete=True
    )

def test_fractal_swing_identification():
    # 5 candles: middle candle is the highest
    candles = [
        make_candle(0, 1.1000, 1.1020, 1.0990, 1.1010),
        make_candle(1, 1.1010, 1.1030, 1.1000, 1.1025),
        make_candle(2, 1.1025, 1.1060, 1.1020, 1.1050), # Swing High (1.1060)
        make_candle(3, 1.1050, 1.1040, 1.1010, 1.1020),
        make_candle(4, 1.1020, 1.1030, 1.0980, 1.0990),
    ]

    swings = MarketStructureAnalyzer.identify_swings(candles, left_bars=2, right_bars=2)
    high_swings = [s for s in swings if s.point_type == "HIGH"]
    assert len(high_swings) == 1
    assert high_swings[0].price == 1.1060
    assert high_swings[0].index == 2

def test_fair_value_gap_detection():
    # Bullish FVG: Bar 0 High < Bar 2 Low
    candles = [
        make_candle(0, 1.0800, 1.0820, 1.0790, 1.0815), # High = 1.0820
        make_candle(1, 1.0815, 1.0870, 1.0810, 1.0865), # Large expansion bar
        make_candle(2, 1.0865, 1.0890, 1.0840, 1.0880), # Low = 1.0840 > 1.0820
    ]

    fvgs = MarketStructureAnalyzer.detect_fair_value_gaps(candles, pip_size=0.0001)
    assert len(fvgs) == 1
    assert fvgs[0].fvg_type == "BULLISH"
    assert fvgs[0].bottom_price == 1.0820
    assert fvgs[0].top_price == 1.0840
    assert fvgs[0].gap_size_pips == 20.0
    assert fvgs[0].mitigated is False

def test_liquidity_sweep_detection():
    # Reference high at 1.0850.
    # Current candle wicks to 1.0870 (+20 pips), but closes back inside at 1.0845.
    candle = make_candle(5, 1.0830, 1.0870, 1.0825, 1.0845)

    sweeps = MarketStructureAnalyzer.detect_liquidity_sweep(
        current_candle=candle,
        reference_high=1.0850,
        reference_low=1.0800,
        pip_size=0.0001,
        level_label_prefix="ASIAN"
    )

    assert len(sweeps) == 1
    assert sweeps[0].level_type == "ASIAN_HIGH"
    assert sweeps[0].level_price == 1.0850
    assert sweeps[0].extreme_price == 1.0870
    assert sweeps[0].sweep_depth_pips == 20.0
    assert sweeps[0].closed_inside is True

def test_candle_structure_pin_bar():
    # Long upper wick, small body at bottom
    # Open=1.0810, High=1.0860, Low=1.0808, Close=1.0812
    # Total range = 52 pips, Upper wick = 48 pips (92%), Body = 2 pips
    pin_candle = make_candle(0, 1.0810, 1.0860, 1.0808, 1.0812)
    analysis = MarketStructureAnalyzer.analyze_candle_structure(pin_candle, pip_size=0.0001)

    assert analysis.is_pin_bar is True
    assert analysis.upper_wick_pips == 48.0
    assert analysis.body_pips == 2.0

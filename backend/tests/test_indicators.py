import pytest
from app.services.features.indicators import TechnicalIndicators

def test_ema_calculation():
    # 5-period EMA with simple step numbers
    closes = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0]
    emas = TechnicalIndicators.calculate_ema(closes, period=5)

    # First 4 must be None
    assert emas[:4] == [None, None, None, None]
    # 5th element is initial SMA: (10 + 11 + 12 + 13 + 14) / 5 = 12.0
    assert emas[4] == 12.0
    # 6th element: alpha = 2 / (5 + 1) = 1/3. EMA = 15*(1/3) + 12*(2/3) = 5 + 8 = 13.0
    assert emas[5] == 13.0
    # 7th element: 16*(1/3) + 13*(2/3) = 5.333333 + 8.666667 = 14.0
    assert emas[6] == 14.0

def test_atr_calculation():
    highs =  [10.0, 12.0, 11.0, 13.0, 15.0]
    lows =   [ 8.0,  9.0,  9.5, 10.0, 11.0]
    closes = [ 9.0, 10.0, 10.5, 12.0, 14.0]

    # Period 3 ATR
    # TR0 = 10 - 8 = 2.0
    # TR1 = max(12 - 9=3, |12 - 9|=3, |9 - 9|=0) = 3.0
    # TR2 = max(11 - 9.5=1.5, |11 - 10|=1, |9.5 - 10|=0.5) = 1.5
    # Initial ATR = (2.0 + 3.0 + 1.5) / 3 = 2.166667
    atrs = TechnicalIndicators.calculate_atr(highs, lows, closes, period=3)
    assert atrs[:2] == [None, None]
    assert round(atrs[2], 2) == 2.17

def test_rsi_calculation_all_gains():
    # Continual upward trend should produce RSI = 100
    closes = [float(i) for i in range(1, 25)]
    rsis = TechnicalIndicators.calculate_rsi(closes, period=14)
    assert rsis[-1] == 100.0

def test_rsi_calculation_all_losses():
    # Continual downward trend should produce RSI = 0
    closes = [float(100 - i) for i in range(1, 25)]
    rsis = TechnicalIndicators.calculate_rsi(closes, period=14)
    assert rsis[-1] == 0.0

def test_macd_calculation():
    # 35 closing prices
    closes = [100.0 + (i * 0.5) for i in range(35)]
    macd_res = TechnicalIndicators.calculate_macd(closes, fast_period=12, slow_period=26, signal_period=9)

    assert "macd" in macd_res
    assert "signal" in macd_res
    assert "histogram" in macd_res
    assert len(macd_res["macd"]) == 35
    # Slow EMA requires 26 bars, so early bars are None
    assert macd_res["macd"][0] is None
    assert macd_res["macd"][-1] is not None

def test_adx_calculation():
    highs =  [100.0 + i for i in range(40)]
    lows =   [ 98.0 + i for i in range(40)]
    closes = [ 99.0 + i for i in range(40)]

    adx_res = TechnicalIndicators.calculate_adx(highs, lows, closes, period=14)
    assert "adx" in adx_res
    assert "plus_di" in adx_res
    assert "minus_di" in adx_res
    # In a pure strong uptrend, plus_di > minus_di
    assert adx_res["plus_di"][-1] > adx_res["minus_di"][-1]

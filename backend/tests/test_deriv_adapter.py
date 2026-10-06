import pytest
from datetime import datetime, timezone
from app.services.market_data.deriv import DerivMarketDataProvider, DERIV_SYMBOL_MAP, DERIV_TIMEFRAME_MAP

def test_deriv_symbol_mapping_all_instruments():
    provider = DerivMarketDataProvider()
    expected = {
        "XAUUSD": "frxXAUUSD",
        "XAGUSD": "frxXAGUSD",
        "EURUSD": "frxEURUSD",
        "GBPUSD": "frxGBPUSD",
        "USDJPY": "frxUSDJPY",
        "AUDUSD": "frxAUDUSD",
        "USDCHF": "frxUSDCHF",
        "USDCAD": "frxUSDCAD",
    }
    for standard, mapped in expected.items():
        assert provider.map_symbol(standard) == mapped
        assert provider.unmap_symbol(mapped) == standard

def test_deriv_timeframe_granularity_seconds():
    provider = DerivMarketDataProvider()
    expected = {
        "1m": 60,
        "5m": 300,
        "15m": 900,
        "1h": 3600,
        "4h": 14400,
        "1d": 86400,
    }
    for tf, seconds in expected.items():
        assert provider.get_timeframe_seconds(tf) == seconds
        assert DERIV_TIMEFRAME_MAP[tf] == seconds

def test_deriv_timeframe_seconds_invalid():
    provider = DerivMarketDataProvider()
    with pytest.raises(ValueError):
        provider.get_timeframe_seconds("3m")

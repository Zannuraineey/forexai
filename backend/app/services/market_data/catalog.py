from typing import List, Dict, Any, Optional

DERIV_CATALOG: List[Dict[str, Any]] = [
    # --- COMMODITIES / METALS ---
    {
        "symbol": "XAUUSD",
        "deriv_symbol": "frxXAUUSD",
        "display_name": "Gold / USD",
        "market": "commodities",
        "submarket": "metals",
        "base_asset": "XAU",
        "quote_asset": "USD",
        "pip_size": 0.01,
        "default_active": True,
    },
    {
        "symbol": "XAGUSD",
        "deriv_symbol": "frxXAGUSD",
        "display_name": "Silver / USD",
        "market": "commodities",
        "submarket": "metals",
        "base_asset": "XAG",
        "quote_asset": "USD",
        "pip_size": 0.0001,
        "default_active": True,
    },
    {
        "symbol": "XPTUSD",
        "deriv_symbol": "frxXPTUSD",
        "display_name": "Platinum / USD",
        "market": "commodities",
        "submarket": "metals",
        "base_asset": "XPT",
        "quote_asset": "USD",
        "pip_size": 0.01,
        "default_active": False,
    },
    {
        "symbol": "XPDUSD",
        "deriv_symbol": "frxXPDUSD",
        "display_name": "Palladium / USD",
        "market": "commodities",
        "submarket": "metals",
        "base_asset": "XPD",
        "quote_asset": "USD",
        "pip_size": 0.01,
        "default_active": False,
    },

    # --- FOREX: MAJOR PAIRS ---
    {
        "symbol": "EURUSD",
        "deriv_symbol": "frxEURUSD",
        "display_name": "EUR / USD",
        "market": "forex",
        "submarket": "major_pairs",
        "base_asset": "EUR",
        "quote_asset": "USD",
        "pip_size": 0.0001,
        "default_active": True,
    },
    {
        "symbol": "GBPUSD",
        "deriv_symbol": "frxGBPUSD",
        "display_name": "GBP / USD",
        "market": "forex",
        "submarket": "major_pairs",
        "base_asset": "GBP",
        "quote_asset": "USD",
        "pip_size": 0.0001,
        "default_active": True,
    },
    {
        "symbol": "USDJPY",
        "deriv_symbol": "frxUSDJPY",
        "display_name": "USD / JPY",
        "market": "forex",
        "submarket": "major_pairs",
        "base_asset": "USD",
        "quote_asset": "JPY",
        "pip_size": 0.01,
        "default_active": True,
    },
    {
        "symbol": "AUDUSD",
        "deriv_symbol": "frxAUDUSD",
        "display_name": "AUD / USD",
        "market": "forex",
        "submarket": "major_pairs",
        "base_asset": "AUD",
        "quote_asset": "USD",
        "pip_size": 0.0001,
        "default_active": True,
    },
    {
        "symbol": "USDCHF",
        "deriv_symbol": "frxUSDCHF",
        "display_name": "USD / CHF",
        "market": "forex",
        "submarket": "major_pairs",
        "base_asset": "USD",
        "quote_asset": "CHF",
        "pip_size": 0.0001,
        "default_active": True,
    },
    {
        "symbol": "USDCAD",
        "deriv_symbol": "frxUSDCAD",
        "display_name": "USD / CAD",
        "market": "forex",
        "submarket": "major_pairs",
        "base_asset": "USD",
        "quote_asset": "CAD",
        "pip_size": 0.0001,
        "default_active": True,
    },
    {
        "symbol": "AUDJPY",
        "deriv_symbol": "frxAUDJPY",
        "display_name": "AUD / JPY",
        "market": "forex",
        "submarket": "major_pairs",
        "base_asset": "AUD",
        "quote_asset": "JPY",
        "pip_size": 0.01,
        "default_active": False,
    },
    {
        "symbol": "EURJPY",
        "deriv_symbol": "frxEURJPY",
        "display_name": "EUR / JPY",
        "market": "forex",
        "submarket": "major_pairs",
        "base_asset": "EUR",
        "quote_asset": "JPY",
        "pip_size": 0.01,
        "default_active": False,
    },
    {
        "symbol": "GBPJPY",
        "deriv_symbol": "frxGBPJPY",
        "display_name": "GBP / JPY",
        "market": "forex",
        "submarket": "major_pairs",
        "base_asset": "GBP",
        "quote_asset": "JPY",
        "pip_size": 0.01,
        "default_active": False,
    },

    # --- CRASH & BOOM INDICES (24/7) ---
    {"symbol": "BOOM50", "deriv_symbol": "BOOM50", "display_name": "Boom 50 Index", "market": "synthetic_index", "submarket": "crash_boom", "base_asset": "BOOM", "quote_asset": "USD", "pip_size": 0.001, "default_active": False},
    {"symbol": "BOOM150N", "deriv_symbol": "BOOM150N", "display_name": "Boom 150 Index", "market": "synthetic_index", "submarket": "crash_boom", "base_asset": "BOOM", "quote_asset": "USD", "pip_size": 0.00001, "default_active": False},
    {"symbol": "BOOM300N", "deriv_symbol": "BOOM300N", "display_name": "Boom 300 Index", "market": "synthetic_index", "submarket": "crash_boom", "base_asset": "BOOM", "quote_asset": "USD", "pip_size": 0.001, "default_active": False},
    {"symbol": "BOOM500", "deriv_symbol": "BOOM500", "display_name": "Boom 500 Index", "market": "synthetic_index", "submarket": "crash_boom", "base_asset": "BOOM", "quote_asset": "USD", "pip_size": 0.001, "default_active": False},
    {"symbol": "BOOM600", "deriv_symbol": "BOOM600", "display_name": "Boom 600 Index", "market": "synthetic_index", "submarket": "crash_boom", "base_asset": "BOOM", "quote_asset": "USD", "pip_size": 0.001, "default_active": False},
    {"symbol": "BOOM900", "deriv_symbol": "BOOM900", "display_name": "Boom 900 Index", "market": "synthetic_index", "submarket": "crash_boom", "base_asset": "BOOM", "quote_asset": "USD", "pip_size": 0.001, "default_active": False},
    {"symbol": "BOOM1000", "deriv_symbol": "BOOM1000", "display_name": "Boom 1000 Index", "market": "synthetic_index", "submarket": "crash_boom", "base_asset": "BOOM", "quote_asset": "USD", "pip_size": 0.001, "default_active": False},
    {"symbol": "CRASH50", "deriv_symbol": "CRASH50", "display_name": "Crash 50 Index", "market": "synthetic_index", "submarket": "crash_boom", "base_asset": "CRASH", "quote_asset": "USD", "pip_size": 0.001, "default_active": False},
    {"symbol": "CRASH150N", "deriv_symbol": "CRASH150N", "display_name": "Crash 150 Index", "market": "synthetic_index", "submarket": "crash_boom", "base_asset": "CRASH", "quote_asset": "USD", "pip_size": 0.00001, "default_active": False},
    {"symbol": "CRASH300N", "deriv_symbol": "CRASH300N", "display_name": "Crash 300 Index", "market": "synthetic_index", "submarket": "crash_boom", "base_asset": "CRASH", "quote_asset": "USD", "pip_size": 0.001, "default_active": False},
    {"symbol": "CRASH500", "deriv_symbol": "CRASH500", "display_name": "Crash 500 Index", "market": "synthetic_index", "submarket": "crash_boom", "base_asset": "CRASH", "quote_asset": "USD", "pip_size": 0.001, "default_active": False},
    {"symbol": "CRASH600", "deriv_symbol": "CRASH600", "display_name": "Crash 600 Index", "market": "synthetic_index", "submarket": "crash_boom", "base_asset": "CRASH", "quote_asset": "USD", "pip_size": 0.001, "default_active": False},
    {"symbol": "CRASH900", "deriv_symbol": "CRASH900", "display_name": "Crash 900 Index", "market": "synthetic_index", "submarket": "crash_boom", "base_asset": "CRASH", "quote_asset": "USD", "pip_size": 0.001, "default_active": False},
    {"symbol": "CRASH1000", "deriv_symbol": "CRASH1000", "display_name": "Crash 1000 Index", "market": "synthetic_index", "submarket": "crash_boom", "base_asset": "CRASH", "quote_asset": "USD", "pip_size": 0.001, "default_active": False},

    # --- CURRENCY & COMMODITY BASKETS ---
    {"symbol": "WLDUSD", "deriv_symbol": "WLDUSD", "display_name": "USD Basket", "market": "synthetic_index", "submarket": "baskets", "base_asset": "USD", "quote_asset": "BSK", "pip_size": 0.001, "default_active": False},
    {"symbol": "WLDEUR", "deriv_symbol": "WLDEUR", "display_name": "EUR Basket", "market": "synthetic_index", "submarket": "baskets", "base_asset": "EUR", "quote_asset": "BSK", "pip_size": 0.001, "default_active": False},
    {"symbol": "WLDGBP", "deriv_symbol": "WLDGBP", "display_name": "GBP Basket", "market": "synthetic_index", "submarket": "baskets", "base_asset": "GBP", "quote_asset": "BSK", "pip_size": 0.001, "default_active": False},
    {"symbol": "WLDAUD", "deriv_symbol": "WLDAUD", "display_name": "AUD Basket", "market": "synthetic_index", "submarket": "baskets", "base_asset": "AUD", "quote_asset": "BSK", "pip_size": 0.001, "default_active": False},
    {"symbol": "WLDXAU", "deriv_symbol": "WLDXAU", "display_name": "Gold Basket", "market": "synthetic_index", "submarket": "baskets", "base_asset": "XAU", "quote_asset": "BSK", "pip_size": 0.001, "default_active": False},

    # --- RANGE BREAK INDICES ---
    {"symbol": "RB100", "deriv_symbol": "RB100", "display_name": "Range Break 100 Index", "market": "synthetic_index", "submarket": "range_break", "base_asset": "RB", "quote_asset": "USD", "pip_size": 0.1, "default_active": False},
    {"symbol": "RB200", "deriv_symbol": "RB200", "display_name": "Range Break 200 Index", "market": "synthetic_index", "submarket": "range_break", "base_asset": "RB", "quote_asset": "USD", "pip_size": 0.1, "default_active": False},

    # --- DAILY RESET INDICES ---
    {"symbol": "RDBULL", "deriv_symbol": "RDBULL", "display_name": "Bull Market Index", "market": "synthetic_index", "submarket": "daily_reset", "base_asset": "BULL", "quote_asset": "USD", "pip_size": 0.0001, "default_active": False},
    {"symbol": "RDBEAR", "deriv_symbol": "RDBEAR", "display_name": "Bear Market Index", "market": "synthetic_index", "submarket": "daily_reset", "base_asset": "BEAR", "quote_asset": "USD", "pip_size": 0.0001, "default_active": False},

    # --- VOLATILITY (RANDOM) INDICES (2-second ticks) ---
    {"symbol": "R_10", "deriv_symbol": "R_10", "display_name": "Volatility 10 Index", "market": "synthetic_index", "submarket": "volatility", "base_asset": "VOL", "quote_asset": "USD", "pip_size": 0.001, "default_active": False},
    {"symbol": "R_25", "deriv_symbol": "R_25", "display_name": "Volatility 25 Index", "market": "synthetic_index", "submarket": "volatility", "base_asset": "VOL", "quote_asset": "USD", "pip_size": 0.001, "default_active": False},
    {"symbol": "R_50", "deriv_symbol": "R_50", "display_name": "Volatility 50 Index", "market": "synthetic_index", "submarket": "volatility", "base_asset": "VOL", "quote_asset": "USD", "pip_size": 0.0001, "default_active": False},
    {"symbol": "R_75", "deriv_symbol": "R_75", "display_name": "Volatility 75 Index", "market": "synthetic_index", "submarket": "volatility", "base_asset": "VOL", "quote_asset": "USD", "pip_size": 0.0001, "default_active": False},
    {"symbol": "R_100", "deriv_symbol": "R_100", "display_name": "Volatility 100 Index", "market": "synthetic_index", "submarket": "volatility", "base_asset": "VOL", "quote_asset": "USD", "pip_size": 0.01, "default_active": False},

    # --- VOLATILITY (1-SECOND) INDICES (1s ticks) ---
    {"symbol": "1HZ10V", "deriv_symbol": "1HZ10V", "display_name": "Volatility 10 (1s) Index", "market": "synthetic_index", "submarket": "volatility", "base_asset": "VOL1S", "quote_asset": "USD", "pip_size": 0.01, "default_active": False},
    {"symbol": "1HZ15V", "deriv_symbol": "1HZ15V", "display_name": "Volatility 15 (1s) Index", "market": "synthetic_index", "submarket": "volatility", "base_asset": "VOL1S", "quote_asset": "USD", "pip_size": 0.001, "default_active": False},
    {"symbol": "1HZ25V", "deriv_symbol": "1HZ25V", "display_name": "Volatility 25 (1s) Index", "market": "synthetic_index", "submarket": "volatility", "base_asset": "VOL1S", "quote_asset": "USD", "pip_size": 0.01, "default_active": False},
    {"symbol": "1HZ30V", "deriv_symbol": "1HZ30V", "display_name": "Volatility 30 (1s) Index", "market": "synthetic_index", "submarket": "volatility", "base_asset": "VOL1S", "quote_asset": "USD", "pip_size": 0.001, "default_active": False},
    {"symbol": "1HZ50V", "deriv_symbol": "1HZ50V", "display_name": "Volatility 50 (1s) Index", "market": "synthetic_index", "submarket": "volatility", "base_asset": "VOL1S", "quote_asset": "USD", "pip_size": 0.01, "default_active": False},
    {"symbol": "1HZ75V", "deriv_symbol": "1HZ75V", "display_name": "Volatility 75 (1s) Index", "market": "synthetic_index", "submarket": "volatility", "base_asset": "VOL1S", "quote_asset": "USD", "pip_size": 0.01, "default_active": False},
    {"symbol": "1HZ90V", "deriv_symbol": "1HZ90V", "display_name": "Volatility 90 (1s) Index", "market": "synthetic_index", "submarket": "volatility", "base_asset": "VOL1S", "quote_asset": "USD", "pip_size": 0.001, "default_active": False},
    {"symbol": "1HZ100V", "deriv_symbol": "1HZ100V", "display_name": "Volatility 100 (1s) Index", "market": "synthetic_index", "submarket": "volatility", "base_asset": "VOL1S", "quote_asset": "USD", "pip_size": 0.01, "default_active": False},
    {"symbol": "1HZ150V", "deriv_symbol": "1HZ150V", "display_name": "Volatility 150 (1s) Index", "market": "synthetic_index", "submarket": "volatility", "base_asset": "VOL1S", "quote_asset": "USD", "pip_size": 0.01, "default_active": False},
    {"symbol": "1HZ250V", "deriv_symbol": "1HZ250V", "display_name": "Volatility 250 (1s) Index", "market": "synthetic_index", "submarket": "volatility", "base_asset": "VOL1S", "quote_asset": "USD", "pip_size": 0.01, "default_active": False},

    # --- JUMP INDICES ---
    {"symbol": "JD10", "deriv_symbol": "JD10", "display_name": "Jump 10 Index", "market": "synthetic_index", "submarket": "jump_step", "base_asset": "JUMP", "quote_asset": "USD", "pip_size": 0.01, "default_active": False},
    {"symbol": "JD25", "deriv_symbol": "JD25", "display_name": "Jump 25 Index", "market": "synthetic_index", "submarket": "jump_step", "base_asset": "JUMP", "quote_asset": "USD", "pip_size": 0.01, "default_active": False},
    {"symbol": "JD50", "deriv_symbol": "JD50", "display_name": "Jump 50 Index", "market": "synthetic_index", "submarket": "jump_step", "base_asset": "JUMP", "quote_asset": "USD", "pip_size": 0.01, "default_active": False},
    {"symbol": "JD75", "deriv_symbol": "JD75", "display_name": "Jump 75 Index", "market": "synthetic_index", "submarket": "jump_step", "base_asset": "JUMP", "quote_asset": "USD", "pip_size": 0.01, "default_active": False},
    {"symbol": "JD100", "deriv_symbol": "JD100", "display_name": "Jump 100 Index", "market": "synthetic_index", "submarket": "jump_step", "base_asset": "JUMP", "quote_asset": "USD", "pip_size": 0.01, "default_active": False},

    # --- STEP INDICES ---
    {"symbol": "stpRNG", "deriv_symbol": "stpRNG", "display_name": "Step Index", "market": "synthetic_index", "submarket": "jump_step", "base_asset": "STEP", "quote_asset": "USD", "pip_size": 0.1, "default_active": False},

    # --- DEX INDICES ---
    {"symbol": "DEX600UP", "deriv_symbol": "DEX600UP", "display_name": "DEX 600 UP Index", "market": "synthetic_index", "submarket": "dex", "base_asset": "DEX", "quote_asset": "USD", "pip_size": 0.01, "default_active": False},
    {"symbol": "DEX600DN", "deriv_symbol": "DEX600DN", "display_name": "DEX 600 DOWN Index", "market": "synthetic_index", "submarket": "dex", "base_asset": "DEX", "quote_asset": "USD", "pip_size": 0.01, "default_active": False},
    {"symbol": "DEX900UP", "deriv_symbol": "DEX900UP", "display_name": "DEX 900 UP Index", "market": "synthetic_index", "submarket": "dex", "base_asset": "DEX", "quote_asset": "USD", "pip_size": 0.01, "default_active": False},
    {"symbol": "DEX900DN", "deriv_symbol": "DEX900DN", "display_name": "DEX 900 DOWN Index", "market": "synthetic_index", "submarket": "dex", "base_asset": "DEX", "quote_asset": "USD", "pip_size": 0.01, "default_active": False},
    {"symbol": "DEX1500UP", "deriv_symbol": "DEX1500UP", "display_name": "DEX 1500 UP Index", "market": "synthetic_index", "submarket": "dex", "base_asset": "DEX", "quote_asset": "USD", "pip_size": 0.01, "default_active": False},
    {"symbol": "DEX1500DN", "deriv_symbol": "DEX1500DN", "display_name": "DEX 1500 DOWN Index", "market": "synthetic_index", "submarket": "dex", "base_asset": "DEX", "quote_asset": "USD", "pip_size": 0.01, "default_active": False},

    # --- AMERICAS OTC INDICES ---
    {"symbol": "OTC_SPC", "deriv_symbol": "OTC_SPC", "display_name": "US 500 (S&P 500)", "market": "indices", "submarket": "americas_otc", "base_asset": "SPC", "quote_asset": "USD", "pip_size": 0.01, "default_active": False},
    {"symbol": "OTC_NDX", "deriv_symbol": "OTC_NDX", "display_name": "US Tech 100 (Nasdaq)", "market": "indices", "submarket": "americas_otc", "base_asset": "NDX", "quote_asset": "USD", "pip_size": 0.01, "default_active": False},
    {"symbol": "OTC_DJI", "deriv_symbol": "OTC_DJI", "display_name": "Wall Street 30 (Dow Jones)", "market": "indices", "submarket": "americas_otc", "base_asset": "DJI", "quote_asset": "USD", "pip_size": 0.01, "default_active": False},

    # --- EUROPE OTC INDICES ---
    {"symbol": "OTC_GDAXI", "deriv_symbol": "OTC_GDAXI", "display_name": "Germany 40 (DAX)", "market": "indices", "submarket": "europe_otc", "base_asset": "DAX", "quote_asset": "EUR", "pip_size": 0.01, "default_active": False},
    {"symbol": "OTC_FTSE", "deriv_symbol": "OTC_FTSE", "display_name": "UK 100 (FTSE)", "market": "indices", "submarket": "europe_otc", "base_asset": "FTSE", "quote_asset": "GBP", "pip_size": 0.01, "default_active": False},
    {"symbol": "OTC_FCHI", "deriv_symbol": "OTC_FCHI", "display_name": "France 40 (CAC 40)", "market": "indices", "submarket": "europe_otc", "base_asset": "CAC", "quote_asset": "EUR", "pip_size": 0.01, "default_active": False},
    {"symbol": "OTC_SX5E", "deriv_symbol": "OTC_SX5E", "display_name": "Euro 50 (Euro Stoxx 50)", "market": "indices", "submarket": "europe_otc", "base_asset": "SX5E", "quote_asset": "EUR", "pip_size": 0.01, "default_active": False},
    {"symbol": "OTC_AEX", "deriv_symbol": "OTC_AEX", "display_name": "Netherlands 25 (AEX)", "market": "indices", "submarket": "europe_otc", "base_asset": "AEX", "quote_asset": "EUR", "pip_size": 0.01, "default_active": False},
    {"symbol": "OTC_SSMI", "deriv_symbol": "OTC_SSMI", "display_name": "Swiss 20 (SMI)", "market": "indices", "submarket": "europe_otc", "base_asset": "SMI", "quote_asset": "CHF", "pip_size": 0.01, "default_active": False},

    # --- ASIA / OCEANIA OTC INDICES ---
    {"symbol": "OTC_N225", "deriv_symbol": "OTC_N225", "display_name": "Japan 225 (Nikkei)", "market": "indices", "submarket": "asia_otc", "base_asset": "N225", "quote_asset": "JPY", "pip_size": 0.01, "default_active": False},
    {"symbol": "OTC_HSI", "deriv_symbol": "OTC_HSI", "display_name": "Hong Kong 50 (Hang Seng)", "market": "indices", "submarket": "asia_otc", "base_asset": "HSI", "quote_asset": "HKD", "pip_size": 0.01, "default_active": False},
    {"symbol": "OTC_AS51", "deriv_symbol": "OTC_AS51", "display_name": "Australia 200 (ASX)", "market": "indices", "submarket": "asia_otc", "base_asset": "AS51", "quote_asset": "AUD", "pip_size": 0.01, "default_active": False},

    # --- CRYPTOCURRENCY ---
    {"symbol": "BTCUSD", "deriv_symbol": "cryBTCUSD", "display_name": "Bitcoin / USD", "market": "cryptocurrency", "submarket": "crypto", "base_asset": "BTC", "quote_asset": "USD", "pip_size": 0.01, "default_active": False},
    {"symbol": "ETHUSD", "deriv_symbol": "cryETHUSD", "display_name": "Ethereum / USD", "market": "cryptocurrency", "submarket": "crypto", "base_asset": "ETH", "quote_asset": "USD", "pip_size": 0.01, "default_active": False},
]

CATALOG_BY_SYMBOL: Dict[str, Dict[str, Any]] = {item["symbol"]: item for item in DERIV_CATALOG}
DERIV_TO_STANDARD_MAP: Dict[str, str] = {item["deriv_symbol"]: item["symbol"] for item in DERIV_CATALOG}
STANDARD_TO_DERIV_MAP: Dict[str, str] = {item["symbol"]: item["deriv_symbol"] for item in DERIV_CATALOG}

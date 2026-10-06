from app.services.market_data.base import IMarketDataProvider, TIMEFRAME_SECONDS_MAP
from app.services.market_data.deriv import DerivMarketDataProvider
from app.services.market_data.mock_provider import MockMarketDataProvider
from app.services.market_data.gap_recovery import GapRecoveryEngine
from app.services.market_data.ingestion_worker import IngestionWorker

def get_market_data_provider(provider_name: str = "deriv") -> IMarketDataProvider:
    """Factory to instantiate the appropriate market data provider."""
    if provider_name.lower() == "deriv":
        return DerivMarketDataProvider()
    elif provider_name.lower() == "mock":
        return MockMarketDataProvider()
    else:
        raise ValueError(f"Unknown market data provider: {provider_name}")

__all__ = [
    "IMarketDataProvider",
    "TIMEFRAME_SECONDS_MAP",
    "DerivMarketDataProvider",
    "MockMarketDataProvider",
    "GapRecoveryEngine",
    "IngestionWorker",
    "get_market_data_provider",
]

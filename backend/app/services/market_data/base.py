from abc import ABC, abstractmethod
from datetime import datetime
from typing import AsyncGenerator, List, Optional
from app.schemas.candle import CandleDTO

TIMEFRAME_SECONDS_MAP = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
}

class IMarketDataProvider(ABC):
    """
    Abstract interface for market data ingestion.
    Allows seamlessly swapping Deriv with other providers (e.g. OANDA, Interactive Brokers,
    MetaTrader gateway, Alpaca) without altering downstream business logic or database layers.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier (e.g. 'deriv', 'mock')."""
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Connection status."""
        pass

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection with credentials and heartbeat."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Gracefully terminate connection."""
        pass

    @abstractmethod
    def map_symbol(self, standard_symbol: str) -> str:
        """Convert standard symbol (e.g. 'EURUSD') to provider symbol (e.g. 'frxEURUSD')."""
        pass

    @abstractmethod
    def unmap_symbol(self, provider_symbol: str) -> str:
        """Convert provider symbol back to standard symbol."""
        pass

    @classmethod
    def get_timeframe_seconds(cls, timeframe: str) -> int:
        """Get duration in seconds for timeframe."""
        if timeframe not in TIMEFRAME_SECONDS_MAP:
            raise ValueError(f"Unsupported timeframe: {timeframe}. Allowed: {list(TIMEFRAME_SECONDS_MAP.keys())}")
        return TIMEFRAME_SECONDS_MAP[timeframe]

    @abstractmethod
    async def fetch_historical_candles(
        self,
        symbol: str,
        timeframe: str,
        start_time: datetime,
        end_time: datetime,
        count: Optional[int] = None,
    ) -> List[CandleDTO]:
        """
        Fetch a batch of historical OHLC candles between start_time and end_time.
        Times must be UTC. Returns sorted ascending by timestamp_utc.
        """
        pass

    @abstractmethod
    async def subscribe_live_candles(
        self,
        symbols: List[str],
        timeframes: List[str],
    ) -> AsyncGenerator[CandleDTO, None]:
        """
        Yields live candle updates for the subscribed symbols and timeframes.
        """
        pass

import asyncio
import math
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator, List, Optional
from app.schemas.candle import CandleDTO
from app.services.market_data.base import IMarketDataProvider, TIMEFRAME_SECONDS_MAP

class MockMarketDataProvider(IMarketDataProvider):
    """
    Deterministic mock provider for automated unit tests, offline development,
    and gap recovery validation. Generates realistic synthetic price curves.
    """

    def __init__(self, base_price: float = 1.0850):
        self._base_price = base_price
        self._connected = False
        self._live_queue: asyncio.Queue[CandleDTO] = asyncio.Queue()
        self._sim_task: Optional[asyncio.Task] = None

    @property
    def name(self) -> str:
        return "mock"

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False
        if self._sim_task and not self._sim_task.done():
            self._sim_task.cancel()

    def map_symbol(self, standard_symbol: str) -> str:
        return standard_symbol

    def unmap_symbol(self, provider_symbol: str) -> str:
        return provider_symbol

    def _generate_synthetic_candle(
        self, symbol: str, timeframe: str, ts_utc: datetime, seed_offset: int = 0
    ) -> CandleDTO:
        """Deterministic price calculation based on timestamp sine/cosine."""
        epoch = int(ts_utc.timestamp())
        wave1 = math.sin((epoch + seed_offset) / 3600.0) * 0.0050
        wave2 = math.cos((epoch + seed_offset) / 86400.0) * 0.0120
        open_price = round(self._base_price + wave1 + wave2, 5)
        
        # High, Low, Close derived from deterministic micro-variations
        spread = 0.0008
        high_price = round(open_price + spread * (1.0 + abs(math.sin(epoch % 77))), 5)
        low_price = round(open_price - spread * (1.0 + abs(math.cos(epoch % 53))), 5)
        close_price = round((open_price + high_price + low_price) / 3.0, 5)

        return CandleDTO(
            symbol=symbol,
            timeframe=timeframe,
            timestamp_utc=ts_utc,
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=100.0 + (epoch % 50),
            provider="mock",
            is_complete=True
        )

    async def fetch_historical_candles(
        self,
        symbol: str,
        timeframe: str,
        start_time: datetime,
        end_time: datetime,
        count: Optional[int] = None,
    ) -> List[CandleDTO]:
        tf_seconds = self.get_timeframe_seconds(timeframe)
        current_ts = start_time.replace(microsecond=0)
        
        # Align to timeframe boundary
        epoch = int(current_ts.timestamp())
        remainder = epoch % tf_seconds
        if remainder != 0:
            current_ts = datetime.fromtimestamp(epoch - remainder, tz=timezone.utc)

        results: List[CandleDTO] = []
        step = timedelta(seconds=tf_seconds)

        while current_ts <= end_time:
            candle = self._generate_synthetic_candle(symbol, timeframe, current_ts)
            results.append(candle)
            current_ts += step
            if count and len(results) >= count:
                break

        return results

    async def subscribe_live_candles(
        self,
        symbols: List[str],
        timeframes: List[str],
    ) -> AsyncGenerator[CandleDTO, None]:
        while self._connected:
            await asyncio.sleep(0.1) # Fast simulation interval
            now = datetime.now(timezone.utc)
            for symbol in symbols:
                for tf in timeframes:
                    candle = self._generate_synthetic_candle(symbol, tf, now)
                    yield candle

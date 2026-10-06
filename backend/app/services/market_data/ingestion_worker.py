import asyncio
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.core.database import async_session_factory
from app.schemas.candle import CandleDTO
from app.services.candle_service import CandleService
from app.services.market_data.base import IMarketDataProvider
from app.services.market_data.gap_recovery import GapRecoveryEngine

class IngestionWorker:
    """
    Continuous market data ingestion supervisor.
    - Executes startup gap-recovery on boot.
    - Manages live websocket subscription with exponential backoff retry.
    - Persists candles asynchronously.
    - Exposes health and recovery status.
    """

    def __init__(
        self,
        provider: IMarketDataProvider,
        symbols: Optional[List[str]] = None,
        timeframes: Optional[List[str]] = None,
    ):
        self.provider = provider
        self.symbols = symbols or settings.TARGET_INSTRUMENTS
        self.timeframes = timeframes or settings.TARGET_TIMEFRAMES
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_candle_received_at: Optional[datetime] = None
        self._total_candles_ingested: int = 0
        self._reconnect_count: int = 0
        self._is_recovering_gaps = False

    @property
    def status(self) -> dict:
        return {
            "is_running": self._running,
            "provider": self.provider.name,
            "is_provider_connected": self.provider.is_connected,
            "is_recovering_gaps": self._is_recovering_gaps,
            "last_candle_received_at": self._last_candle_received_at.isoformat() if self._last_candle_received_at else None,
            "total_candles_ingested": self._total_candles_ingested,
            "reconnect_count": self._reconnect_count,
            "monitored_symbols": self.symbols,
            "monitored_timeframes": self.timeframes,
        }

    async def run_startup_recovery(self) -> None:
        """Run initial gap recovery before listening for live ticks."""
        self._is_recovering_gaps = True
        logger.info("Initiating startup gap recovery check across all instruments...")
        try:
            async with async_session_factory() as session:
                engine = GapRecoveryEngine(session, self.provider)
                reports = await engine.recover_all(self.symbols, self.timeframes)
                total_recovered = sum(r.recovered_bars for r in reports)
                logger.info(f"Startup gap recovery complete. Total recovered bars: {total_recovered}")
        except Exception as e:
            logger.error(f"Error during startup gap recovery: {e}", exc_info=True)
        finally:
            self._is_recovering_gaps = False

    async def start(self) -> None:
        """Start the ingestion supervisor background task."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._supervision_loop())
        logger.info("Ingestion worker started.")

    async def stop(self) -> None:
        """Graceful shutdown of ingestion supervisor."""
        logger.info("Stopping Ingestion worker gracefully...")
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self.provider.disconnect()
        logger.info("Ingestion worker stopped successfully.")

    async def _supervision_loop(self) -> None:
        """Runs connect, gap recovery, and live streaming with exponential backoff on disconnects."""
        backoff = settings.WORKER_INITIAL_BACKOFF_SECONDS
        
        while self._running:
            try:
                # 1. Connect provider
                await self.provider.connect()
                
                # 2. Run gap recovery for any offline interval
                await self.run_startup_recovery()
                
                # Reset backoff on successful connection
                backoff = settings.WORKER_INITIAL_BACKOFF_SECONDS

                # 3. Stream live candles
                batch_buffer: List[CandleDTO] = []
                async for candle in self.provider.subscribe_live_candles(self.symbols, self.timeframes):
                    if not self._running:
                        break
                    
                    self._last_candle_received_at = datetime.now(timezone.utc)
                    await self._persist_batch([candle])

                # Flush remaining
                if batch_buffer:
                    await self._persist_batch(batch_buffer)
                    batch_buffer.clear()

            except asyncio.CancelledError:
                break
            except Exception as e:
                self._reconnect_count += 1
                logger.warning(
                    f"Market data ingestion stream interrupted: {e}. Retrying in {backoff:.1f}s... "
                    f"(Reconnect count: {self._reconnect_count})"
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2.0, settings.WORKER_MAX_BACKOFF_SECONDS)

    async def _persist_batch(self, batch: List[CandleDTO]) -> None:
        """Helper to persist candle batch into database."""
        try:
            async with async_session_factory() as session:
                svc = CandleService(session)
                count = await svc.save_candles(batch)
                self._total_candles_ingested += count
        except Exception as e:
            logger.error(f"Failed to persist live candle batch: {e}", exc_info=True)

import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.core.locks import AdvisoryLockManager
from app.schemas.candle import GapReport
from app.services.candle_service import CandleService
from app.services.market_data.base import IMarketDataProvider

class GapRecoveryEngine:
    """
    Guarantees seamless restart recovery on Render or infrastructure restarts:
    1. Reads latest stored candle from database for each symbol and timeframe.
    2. Identifies duration and count of missing historical bars.
    3. Fetches missing batches from the market data provider (Deriv / pluggable).
    4. Idempotently inserts bars without duplicates.
    5. Returns structured gap resolution metrics.
    """

    def __init__(self, db: AsyncSession, provider: IMarketDataProvider):
        self.db = db
        self.provider = provider
        self.candle_service = CandleService(db)

    async def recover_symbol_timeframe(
        self,
        symbol: str,
        timeframe: str,
        now_utc: Optional[datetime] = None,
        default_lookback_days: int = 7,
    ) -> GapReport:
        now_utc = now_utc or datetime.now(timezone.utc)
        tf_seconds = self.provider.get_timeframe_seconds(timeframe)
        lock_key = f"gap_recovery:{symbol}:{timeframe}"

        # Acquire lock to ensure only one worker performs recovery for this series
        has_lock = await AdvisoryLockManager.try_acquire(self.db, lock_key)
        if not has_lock:
            logger.info(f"Skipping gap recovery for {symbol} {timeframe}; lock already held by another worker.")
            return GapReport(
                symbol=symbol,
                timeframe=timeframe,
                last_stored_timestamp=None,
                now_utc=now_utc,
                gap_duration_seconds=0,
                missing_bars_estimated=0,
                recovered_bars=0,
                status="SKIPPED_LOCKED"
            )

        try:
            inst = await self.candle_service.ensure_instrument(symbol)
            latest_ts = await self.candle_service.get_latest_candle_timestamp(inst.id, timeframe)

            # Determine start time
            if latest_ts is None:
                # First run / cold start: fetch default historical lookback
                start_time = now_utc - timedelta(days=default_lookback_days)
                logger.info(f"Cold start for {symbol} ({timeframe}): seeding past {default_lookback_days} days.")
            else:
                # Make sure timezone is UTC
                if latest_ts.tzinfo is None:
                    latest_ts = latest_ts.replace(tzinfo=timezone.utc)
                start_time = latest_ts + timedelta(seconds=tf_seconds)

            gap_duration = (now_utc - start_time).total_seconds()
            estimated_missing = max(0, int(gap_duration // tf_seconds))

            if estimated_missing <= 0:
                logger.debug(f"{symbol} ({timeframe}) is already up to date. (Gap: {gap_duration:.1f}s)")
                return GapReport(
                    symbol=symbol,
                    timeframe=timeframe,
                    last_stored_timestamp=latest_ts,
                    now_utc=now_utc,
                    gap_duration_seconds=max(0.0, gap_duration),
                    missing_bars_estimated=0,
                    recovered_bars=0,
                    status="UP_TO_DATE"
                )

            logger.info(
                f"Recovering gap for {symbol} ({timeframe}): ~{estimated_missing} bars missing "
                f"from {start_time.isoformat()} to {now_utc.isoformat()}."
            )

            # Fetch missing candles from provider
            recovered_candles = await self.provider.fetch_historical_candles(
                symbol=symbol,
                timeframe=timeframe,
                start_time=start_time,
                end_time=now_utc,
                count=min(estimated_missing + 10, settings.MAX_HISTORICAL_BARS_PER_REQUEST)
            )

            # Save recovered bars idempotently
            saved_count = await self.candle_service.save_candles(recovered_candles)
            logger.info(f"Successfully recovered {saved_count} candles for {symbol} ({timeframe}).")

            return GapReport(
                symbol=symbol,
                timeframe=timeframe,
                last_stored_timestamp=latest_ts,
                now_utc=now_utc,
                gap_duration_seconds=gap_duration,
                missing_bars_estimated=estimated_missing,
                recovered_bars=saved_count,
                status="RECOVERED"
            )

        finally:
            await AdvisoryLockManager.release(self.db, lock_key)

    async def recover_all(
        self,
        symbols: Optional[List[str]] = None,
        timeframes: Optional[List[str]] = None,
        now_utc: Optional[datetime] = None,
    ) -> List[GapReport]:
        """
        Runs gap recovery across all configured symbols and timeframes sequentially or in bounded batches.
        """
        symbols = symbols or settings.TARGET_INSTRUMENTS
        timeframes = timeframes or settings.TARGET_TIMEFRAMES
        reports: List[GapReport] = []

        for symbol in symbols:
            for tf in timeframes:
                report = await self.recover_symbol_timeframe(symbol, tf, now_utc=now_utc)
                reports.append(report)

        return reports

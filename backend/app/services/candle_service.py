from datetime import datetime, timezone
from typing import Dict, List, Optional
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.core.logging import logger
from app.models.instrument import Instrument
from app.models.candle import Candle
from app.schemas.candle import CandleDTO, CandleRead

class CandleService:
    """
    Encapsulates all database interactions for instruments and time-series candles.
    Ensures idempotent bulk persistence and zero-duplicate guarantees across restarts.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def ensure_instrument(self, symbol: str, pip_size: float = 0.0001) -> Instrument:
        """Find or create an instrument record."""
        stmt = select(Instrument).where(Instrument.symbol == symbol)
        result = await self.db.execute(stmt)
        inst = result.scalar_one_or_none()

        if not inst:
            # Determine base and quote
            base = symbol[:3] if len(symbol) >= 6 else symbol
            quote = symbol[3:] if len(symbol) >= 6 else "USD"
            if "JPY" in quote:
                pip_size = 0.01
            elif "XAU" in symbol or "XAG" in symbol:
                pip_size = 0.01

            inst = Instrument(
                symbol=symbol,
                base_asset=base,
                quote_asset=quote,
                pip_size=pip_size,
                is_active=True
            )
            self.db.add(inst)
            await self.db.flush()
            logger.info(f"Initialized new instrument in database: {symbol}")

        return inst

    async def get_instrument_map(self, symbols: List[str]) -> Dict[str, Instrument]:
        """Fetch or create instruments and return symbol -> Instrument mapping."""
        mapping = {}
        for s in symbols:
            mapping[s] = await self.ensure_instrument(s)
        await self.db.commit()
        return mapping

    async def get_latest_candle_timestamp(
        self, instrument_id: int, timeframe: str
    ) -> Optional[datetime]:
        """Returns the most recent UTC timestamp stored for this instrument and timeframe."""
        stmt = (
            select(func.max(Candle.timestamp_utc))
            .where(Candle.instrument_id == instrument_id)
            .where(Candle.timeframe == timeframe)
        )
        result = await self.db.execute(stmt)
        return result.scalar()

    async def save_candles(self, candle_dtos: List[CandleDTO]) -> int:
        """
        Idempotently persists a list of CandleDTOs.
        Uses ON CONFLICT DO NOTHING to guarantee no duplicate candles on Render restarts.
        """
        if not candle_dtos:
            return 0

        # Collect distinct symbols to map to IDs
        symbols = list(set(c.symbol for c in candle_dtos))
        inst_map = await self.get_instrument_map(symbols)

        bind = self.db.bind
        dialect_name = bind.dialect.name if bind else "sqlite"

        records_to_insert = []
        for c in candle_dtos:
            inst = inst_map.get(c.symbol)
            if not inst:
                continue
            records_to_insert.append({
                "instrument_id": inst.id,
                "timeframe": c.timeframe,
                "timestamp_utc": c.timestamp_utc,
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
                "provider": c.provider,
                "is_complete": c.is_complete,
            })

        if not records_to_insert:
            return 0

        # Dialect specific UPSERT with DO UPDATE so live ticks update running candles
        if dialect_name == "postgresql":
            stmt = pg_insert(Candle).values(records_to_insert)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_candle_inst_tf_ts",
                set_={
                    "high": stmt.excluded.high,
                    "low": stmt.excluded.low,
                    "close": stmt.excluded.close,
                    "volume": stmt.excluded.volume,
                    "is_complete": stmt.excluded.is_complete,
                }
            )
            result = await self.db.execute(stmt)
            await self.db.commit()
            return result.rowcount or len(records_to_insert)
        else:
            # SQLite ON CONFLICT DO UPDATE
            stmt = sqlite_insert(Candle).values(records_to_insert)
            stmt = stmt.on_conflict_do_update(
                index_elements=["instrument_id", "timeframe", "timestamp_utc"],
                set_={
                    "high": stmt.excluded.high,
                    "low": stmt.excluded.low,
                    "close": stmt.excluded.close,
                    "volume": stmt.excluded.volume,
                    "is_complete": stmt.excluded.is_complete,
                }
            )
            result = await self.db.execute(stmt)
            await self.db.commit()
            return result.rowcount or len(records_to_insert)

    async def get_candles(
        self,
        symbol: str,
        timeframe: str,
        start_utc: Optional[datetime] = None,
        end_utc: Optional[datetime] = None,
        limit: int = 500,
    ) -> List[CandleRead]:
        """Fetch candles for an instrument, ordered chronologically ascending."""
        inst = await self.ensure_instrument(symbol)
        stmt = (
            select(Candle)
            .where(Candle.instrument_id == inst.id)
            .where(Candle.timeframe == timeframe)
        )
        if start_utc:
            stmt = stmt.where(Candle.timestamp_utc >= start_utc)
        if end_utc:
            stmt = stmt.where(Candle.timestamp_utc <= end_utc)

        stmt = stmt.order_by(Candle.timestamp_utc.desc()).limit(limit)
        result = await self.db.execute(stmt)
        candles = list(result.scalars().all())
        candles.reverse() # Return chronological ascending

        return [CandleRead.model_validate(c) for c in candles]

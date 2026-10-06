import asyncio
import hashlib
from typing import Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import logger

# In-memory lock fallback for SQLite / test environments
_MEMORY_LOCKS = {}
_MEMORY_GLOBAL_LOCK = asyncio.Lock()

class AdvisoryLockManager:
    """
    Provides cluster-safe locking to prevent concurrent workers from ingesting
    or recovering the same symbol/timeframe candle stream simultaneously.
    Uses PostgreSQL advisory locks in production, falling back to asyncio locks in SQLite/tests.
    """

    @staticmethod
    def _generate_lock_id(lock_key: str) -> int:
        """Convert a string key (e.g. 'recovery:EURUSD:15m') into a 64-bit signed integer for pg_advisory_lock."""
        digest = hashlib.md5(lock_key.encode("utf-8")).hexdigest()
        # Convert first 8 bytes to signed 64-bit int
        raw_int = int(digest[:16], 16)
        if raw_int >= 2**63:
            raw_int -= 2**64
        return raw_int

    @classmethod
    async def try_acquire(cls, session: AsyncSession, lock_key: str) -> bool:
        """
        Attempts to acquire an advisory lock without blocking.
        Returns True if acquired, False otherwise.
        """
        bind = session.bind
        dialect_name = bind.dialect.name if bind else ""

        if dialect_name == "postgresql":
            lock_id = cls._generate_lock_id(lock_key)
            result = await session.execute(
                text("SELECT pg_try_advisory_lock(:lock_id)"),
                {"lock_id": lock_id}
            )
            acquired = result.scalar() is True
            logger.debug(f"PG Advisory Lock for '{lock_key}' (ID: {lock_id}) acquired: {acquired}")
            return acquired
        else:
            # Asyncio fallback
            async with _MEMORY_GLOBAL_LOCK:
                if lock_key not in _MEMORY_LOCKS:
                    _MEMORY_LOCKS[lock_key] = asyncio.Lock()
                lock = _MEMORY_LOCKS[lock_key]

            if not lock.locked():
                await lock.acquire()
                return True
            return False

    @classmethod
    async def release(cls, session: AsyncSession, lock_key: str) -> None:
        """Releases an advisory lock."""
        bind = session.bind
        dialect_name = bind.dialect.name if bind else ""

        if dialect_name == "postgresql":
            lock_id = cls._generate_lock_id(lock_key)
            await session.execute(
                text("SELECT pg_advisory_unlock(:lock_id)"),
                {"lock_id": lock_id}
            )
            logger.debug(f"PG Advisory Lock for '{lock_key}' (ID: {lock_id}) released.")
        else:
            async with _MEMORY_GLOBAL_LOCK:
                lock = _MEMORY_LOCKS.get(lock_key)
                if lock and lock.locked():
                    lock.release()

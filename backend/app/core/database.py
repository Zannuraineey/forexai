from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings
from app.core.logging import logger

class Base(DeclarativeBase):
    pass

from sqlalchemy.engine import make_url

FALLBACK_SQLITE_URL = "sqlite+aiosqlite:///./forex_ai.db"

# Choose database URL depending on environment or overrides
def get_engine_url() -> str:
    if settings.ENVIRONMENT == "test":
        return settings.TEST_DATABASE_URL

    raw_url = str(settings.DATABASE_URL or "").strip().strip("'\"").strip()
    if not raw_url or raw_url.startswith("${"):
        logger.warning(
            f"DATABASE_URL is not set or contains an unresolved placeholder ({raw_url!r}). "
            f"Defaulting to persistent SQLite: {FALLBACK_SQLITE_URL}"
        )
        return FALLBACK_SQLITE_URL

    url = raw_url
    # Normalise standard postgresql URLs for SQLAlchemy asyncpg
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    try:
        parsed = make_url(url)
        if not parsed.drivername:
            raise ValueError("No drivername")
        return url
    except Exception as exc:
        logger.warning(
            f"Could not parse DATABASE_URL ({raw_url!r}: {exc}). "
            f"Defaulting to persistent SQLite: {FALLBACK_SQLITE_URL}"
        )
        return FALLBACK_SQLITE_URL

engine = create_async_engine(
    get_engine_url(),
    echo=False,
    pool_pre_ping=True,
    # SQLite in-memory or file doesn't support pool_size / max_overflow
    **({} if "sqlite" in get_engine_url() else {"pool_size": 10, "max_overflow": 20})
)

async_session_factory = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_db() -> None:
    """
    Initialize database tables.
    If PostgreSQL is unreachable or offline, automatically falls back to local
    persistent SQLite (forex_ai.db) so the backend runs seamlessly on Railway / Render.
    """
    global engine, async_session_factory
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info(f"Database tables initialized successfully using {engine.url.drivername}.")
    except Exception as exc:
        if "sqlite" not in str(engine.url):
            logger.warning(
                f"PostgreSQL connection to {engine.url.host or 'database'} failed ({exc}). "
                "Automatically falling back to persistent local SQLite database (sqlite+aiosqlite:///./forex_ai.db)."
            )
            fallback_url = "sqlite+aiosqlite:///./forex_ai.db"
            engine = create_async_engine(fallback_url, echo=False)
            async_session_factory.configure(bind=engine)
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Local SQLite database initialized and ready at ./forex_ai.db.")
        else:
            raise

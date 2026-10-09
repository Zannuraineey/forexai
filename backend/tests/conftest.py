import pytest
import os
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
from app.core.database import Base
import app.models  # noqa: F401 - ensure all tables are registered in Base.metadata

# Force test mode
os.environ["ENVIRONMENT"] = "test"
settings.ENVIRONMENT = "test"

TEST_ENGINE = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    echo=False
)

TestSessionFactory = async_sessionmaker(
    bind=TEST_ENGINE,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession
)

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(autouse=True)
async def prepare_database():
    async with TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionFactory() as session:
        yield session

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import logger
from app.core.database import init_db
from app.api import api_router
from app.services.market_data import get_market_data_provider, IngestionWorker
from app.services.ai import get_session_scanner

ingestion_worker: IngestionWorker | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"Starting {settings.PROJECT_NAME} in [{settings.ENVIRONMENT}] mode...")
    await init_db()

    # In non-test environments or when explicitly requested, launch continuous ingestion supervisor & session scanner
    if settings.ENVIRONMENT != "test":
        provider = get_market_data_provider(settings.DEFAULT_PROVIDER)
        global ingestion_worker
        ingestion_worker = IngestionWorker(provider=provider)
        await ingestion_worker.start()

        # Launch automated 24/7 background session scanner
        scanner = get_session_scanner()
        await scanner.start()

    yield

    # Shutdown
    logger.info("Initiating graceful shutdown...")
    scanner = get_session_scanner()
    await scanner.stop()
    if ingestion_worker:
        await ingestion_worker.stop()
    logger.info("Shutdown completed.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Forex AI Market Analysis Platform - Resilient Ingestion & Analysis Engine",
    version="1.0.0",
    lifespan=lifespan
)

# Cross-Origin Resource Sharing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)
# Also include health check at root /health for simple container pinging
from app.api.health import router as health_root_router
app.include_router(health_root_router)

@app.get("/")
async def root():
    return {
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "docs": "/docs",
        "health": "/health"
    }

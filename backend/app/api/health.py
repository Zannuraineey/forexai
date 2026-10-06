import time
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db

router = APIRouter(prefix="", tags=["Health"])

START_TIME = time.time()

@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Comprehensive system health check for Render and monitoring agents.
    Verifies database connection, query responsiveness, and service uptime.
    """
    db_status = "unhealthy"
    db_latency_ms = None
    try:
        t0 = time.time()
        await db.execute(text("SELECT 1"))
        db_latency_ms = round((time.time() - t0) * 1000, 2)
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    is_overall_healthy = db_status == "healthy"
    uptime_seconds = round(time.time() - START_TIME, 1)

    payload = {
        "status": "ok" if is_overall_healthy else "degraded",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": uptime_seconds,
        "database": {
            "status": db_status,
            "latency_ms": db_latency_ms,
        }
    }

    return payload


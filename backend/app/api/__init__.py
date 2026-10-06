from fastapi import APIRouter
from app.api.health import router as health_router
from app.api.instruments import router as instruments_router
from app.api.candles import router as candles_router
from app.api.market_context import router as context_router
from app.api.sessions import router as sessions_router
from app.api.strategy import router as strategy_router
from app.api.analysis import router as analysis_router
from app.api.notifications import router as notifications_router
from app.api.news import router as news_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(instruments_router)
api_router.include_router(candles_router)
api_router.include_router(context_router)
api_router.include_router(sessions_router)
api_router.include_router(strategy_router)
api_router.include_router(analysis_router)
api_router.include_router(notifications_router)
api_router.include_router(news_router)


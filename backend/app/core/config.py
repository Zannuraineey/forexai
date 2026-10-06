from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "Forex AI Market Analysis Platform"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=True)

    # Database: Async PostgreSQL for production, fallback to aiosqlite for tests/local
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/forex_ai"
    )
    TEST_DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///:memory:"
    )

    # Market Data
    DEFAULT_PROVIDER: str = Field(default="deriv")
    DERIV_APP_ID: str = Field(default="1089") # Default public test app_id or custom
    DERIV_WS_URL: str = Field(default="wss://api.derivws.com/trading/v1/options/ws/public")
    DERIV_API_TOKEN: str = Field(default="")

    # AI Reasoning Models (Gemini, OpenAI, Anthropic, or Local)
    AI_API_KEY: str = Field(default="")
    GEMINI_API_KEY: str = Field(default="")
    OPENAI_API_KEY: str = Field(default="")
    AI_MODEL_NAME: str = Field(default="gemini-1.5-flash")

    # Initial Instruments
    TARGET_INSTRUMENTS: List[str] = [
        "XAUUSD",
        "XAGUSD",
        "EURUSD",
        "GBPUSD",
        "USDJPY",
        "AUDUSD",
        "USDCHF",
        "USDCAD",
        "BTCUSD",
        "R_10",
        "R_25",
        "R_50",
        "R_75",
        "R_100",
        "BOOM1000",
        "CRASH1000",
    ]

    # Target Timeframes (1m, 5m, 15m, 1h, 4h, 1d)
    TARGET_TIMEFRAMES: List[str] = ["1m", "5m", "15m", "1h", "4h", "1d"]

    # Ingestion & Recovery Settings
    MAX_HISTORICAL_BARS_PER_REQUEST: int = 5000
    GAP_RECOVERY_LOOKBACK_DAYS_DEFAULT: int = 14
    WORKER_RECONNECT_MAX_RETRIES: int = 10
    WORKER_INITIAL_BACKOFF_SECONDS: float = 1.0
    WORKER_MAX_BACKOFF_SECONDS: float = 60.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text
from app.core.database import Base

class AIMacroProviderConfig(Base):
    """
    Persistent storage for AI Macro Reasoning Engine provider configuration.
    API keys are encrypted at rest using Fernet and never logged or serialized to clients.
    """
    __tablename__ = "ai_macro_provider_configs"

    user_id = Column(String(64), primary_key=True, default="default_user", index=True)
    provider = Column(String(32), nullable=False, default="groq")
    model = Column(String(64), nullable=False, default="llama-3.3-70b-versatile")
    is_enabled = Column(Boolean, nullable=False, default=True)
    encrypted_api_key = Column(Text, nullable=True)
    api_base_url = Column(String(256), nullable=True)

    # Diagnostic metadata from last connection test
    last_tested_at = Column(DateTime(timezone=True), nullable=True)
    last_test_status = Column(String(32), nullable=True)  # "SUCCESS", "FAILED", "NOT_TESTED"
    last_test_latency_ms = Column(Integer, nullable=True)
    last_test_error = Column(Text, nullable=True)

    created_at_utc = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at_utc = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

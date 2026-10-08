from datetime import datetime, timezone
from typing import Optional
import enum
from sqlalchemy import (
    BigInteger, Integer, String, Text, Boolean, DateTime,
    ForeignKey, UniqueConstraint, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class AnalysisStateEnum(str, enum.Enum):
    NO_SETUP = "NO_SETUP"
    WATCH = "WATCH"
    POTENTIAL_SETUP = "POTENTIAL_SETUP"
    VALID_SETUP = "VALID_SETUP"
    INVALIDATED = "INVALIDATED"

class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    instrument_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("instruments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    candle_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), ForeignKey("candles.id", ondelete="SET NULL"), nullable=True
    )
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    timestamp_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    session_name: Mapped[str] = mapped_column(String(50), nullable=False)
    
    instruction_version_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("instruction_versions.id", ondelete="SET NULL"), nullable=True
    )
    model_version: Mapped[str] = mapped_column(String(100), nullable=False, default="default-v1")
    
    state: Mapped[str] = mapped_column(String(30), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    condition_breakdown: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)
    ambiguities_detected: Mapped[dict] = mapped_column(JSON, nullable=False, default=list)
    full_reasoning: Mapped[str] = mapped_column(Text, nullable=True)
    trade_setup: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=None)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "instrument_id", "timeframe", "timestamp_utc", "instruction_version_id",
            name="uq_analysis_trace"
        ),
    )

class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    analysis_id: Mapped[Optional[int]] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), ForeignKey("analysis_results.id", ondelete="CASCADE"), nullable=True
    )
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    channel: Mapped[str] = mapped_column(String(20), default="fcm")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    fcm_token: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    device_platform: Mapped[str] = mapped_column(String(20), nullable=False) # 'android' / 'ios'
    last_active: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

class Backtest(Base):
    __tablename__ = "backtests"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    instruction_version_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("instruction_versions.id", ondelete="SET NULL"), nullable=True
    )
    instrument_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("instruments.id", ondelete="CASCADE"), nullable=False
    )
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    session_name: Mapped[str] = mapped_column(String(50), nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total_candles_analyzed: Mapped[int] = mapped_column(Integer, default=0)
    state_distribution: Mapped[dict] = mapped_column(JSON, default=dict)
    identified_setups: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(30), default="COMPLETED")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

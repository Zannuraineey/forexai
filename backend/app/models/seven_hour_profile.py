from datetime import datetime, timezone
from sqlalchemy import (
    BigInteger, Integer, String, Numeric, DateTime,
    ForeignKey, UniqueConstraint, Index, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class SevenHourProfile(Base):
    __tablename__ = "seven_hour_profiles"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True
    )
    instrument_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("instruments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    config_id: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC_0000_7H", index=True)
    
    profile_start_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    profile_end_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_timeframe: Mapped[str] = mapped_column(String(10), nullable=False, default="1h")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="COMPLETED") # COMPLETED, IN_PROGRESS
    
    open: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    high: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    low: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    close: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    range: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    body: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    direction: Mapped[str] = mapped_column(String(20), nullable=False) # BULLISH, BEARISH, NEUTRAL
    
    classification: Mapped[str] = mapped_column(String(64), nullable=False)
    relationship_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    quantitative_features: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    data_quality: Mapped[str] = mapped_column(String(20), nullable=False, default="COMPLETE")
    source_candle_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationship
    instrument = relationship("Instrument")

    __table_args__ = (
        UniqueConstraint("instrument_id", "profile_start_utc", "config_id", name="uq_7h_profile_inst_start_config"),
        Index("idx_7h_profile_lookup", "instrument_id", "config_id", "profile_start_utc"),
    )

    def __repr__(self) -> str:
        return (
            f"<SevenHourProfile(inst_id={self.instrument_id}, "
            f"start={self.profile_start_utc.isoformat()}, "
            f"class={self.classification}, status={self.status})>"
        )

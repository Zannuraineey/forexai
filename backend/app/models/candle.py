from datetime import datetime, timezone
from sqlalchemy import (
    BigInteger, Integer, String, Numeric, Boolean, DateTime,
    ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class Candle(Base):
    __tablename__ = "candles"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True
    )
    instrument_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("instruments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False) # 1m, 5m, 15m, 1h, 4h, 1d
    timestamp_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    open: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    high: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    low: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    close: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    volume: Mapped[float] = mapped_column(Numeric(24, 6), nullable=False, default=0.0)
    
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="deriv")
    is_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationship
    instrument = relationship("Instrument", back_populates="candles")

    __table_args__ = (
        UniqueConstraint("instrument_id", "timeframe", "timestamp_utc", name="uq_candle_inst_tf_ts"),
        Index("idx_candles_lookup", "instrument_id", "timeframe", "timestamp_utc"),
    )

    def __repr__(self) -> str:
        return f"<Candle(inst_id={self.instrument_id}, tf={self.timeframe}, ts={self.timestamp_utc.isoformat()}, c={self.close})>"

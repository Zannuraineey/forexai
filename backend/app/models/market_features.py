from datetime import datetime, timezone
from sqlalchemy import (
    BigInteger, Integer, String, DateTime,
    ForeignKey, UniqueConstraint, JSON
)
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class MarketFeature(Base):
    __tablename__ = "market_features"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    candle_id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        ForeignKey("candles.id", ondelete="CASCADE"),
        nullable=True
    )
    instrument_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("instruments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)
    timestamp_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    indicators: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    market_structure: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    liquidity_reference: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint("instrument_id", "timeframe", "timestamp_utc", name="uq_feature_inst_tf_ts"),
    )

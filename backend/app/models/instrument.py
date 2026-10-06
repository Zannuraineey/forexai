from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, Numeric, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class Instrument(Base):
    __tablename__ = "instruments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    base_asset: Mapped[str] = mapped_column(String(10), nullable=False)
    quote_asset: Mapped[str] = mapped_column(String(10), nullable=False)
    pip_size: Mapped[float] = mapped_column(Numeric(10, 6), nullable=False, default=0.0001)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    candles = relationship("Candle", back_populates="instrument", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Instrument(symbol='{self.symbol}', active={self.is_active})>"

from datetime import datetime, timezone
from sqlalchemy import (
    BigInteger, Integer, String, Numeric, DateTime, Boolean, JSON, Index
)
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class TradeSetupOutcome(Base):
    __tablename__ = "trade_setup_outcomes"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True
    )
    setup_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False) # BUY, SELL
    
    entry_signal: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    fill_price: Mapped[float] = mapped_column(Numeric(18, 6), nullable=True) # Actual fill price
    slippage: Mapped[float] = mapped_column(Numeric(18, 6), nullable=True)
    stop_loss: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    take_profit: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    
    signal_timestamp_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    entry_timestamp_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    exit_timestamp_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # MFE / MAE
    max_favorable_excursion: Mapped[float] = mapped_column(Numeric(18, 6), default=0.0, nullable=False)
    max_adverse_excursion: Mapped[float] = mapped_column(Numeric(18, 6), default=0.0, nullable=False)
    mfe_r_multiple: Mapped[float] = mapped_column(Numeric(10, 4), default=0.0, nullable=False)
    mae_r_multiple: Mapped[float] = mapped_column(Numeric(10, 4), default=0.0, nullable=False)
    
    # Milestone times (in seconds)
    time_to_entry_seconds: Mapped[float] = mapped_column(Numeric(14, 2), nullable=True)
    time_to_1r_seconds: Mapped[float] = mapped_column(Numeric(14, 2), nullable=True)
    time_to_2r_seconds: Mapped[float] = mapped_column(Numeric(14, 2), nullable=True)
    time_to_3r_seconds: Mapped[float] = mapped_column(Numeric(14, 2), nullable=True)
    time_to_5r_seconds: Mapped[float] = mapped_column(Numeric(14, 2), nullable=True)
    time_to_tp_seconds: Mapped[float] = mapped_column(Numeric(14, 2), nullable=True)
    time_to_sl_seconds: Mapped[float] = mapped_column(Numeric(14, 2), nullable=True)
    
    reached_1r: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reached_2r: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reached_3r: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reached_5r: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reached_10r: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reached_20r: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reached_sl: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reached_tp: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    outcome: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False) # PENDING, ACTIVE, TP1_HIT, TP2_HIT, SL_HIT, STOPPED_OUT, EXPIRED, CANCELLED
    realized_r_multiple: Mapped[float] = mapped_column(Numeric(10, 4), nullable=True)
    
    # Context snapshot
    setup_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    @property
    def signal_entry(self) -> float:
        return float(self.entry_signal) if self.entry_signal is not None else 0.0

    @signal_entry.setter
    def signal_entry(self, value: float):
        self.entry_signal = value

    @property
    def final_r_multiple(self) -> Optional[float]:
        return float(self.realized_r_multiple) if self.realized_r_multiple is not None else None

    @final_r_multiple.setter
    def final_r_multiple(self, value: Optional[float]):
        self.realized_r_multiple = value
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    __table_args__ = (
        Index("idx_trade_outcome_sym_ts", "symbol", "signal_timestamp_utc"),
    )

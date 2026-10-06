from datetime import datetime, timezone
from sqlalchemy import Integer, String, Boolean, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class StrategyInstruction(Base):
    __tablename__ = "strategy_instructions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    session_name: Mapped[str] = mapped_column(String(50), nullable=False) # 'asian', 'london', 'new_york'
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    current_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    versions = relationship("InstructionVersion", back_populates="instruction", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("user_id", "session_name", name="uq_user_session"),
    )

class InstructionVersion(Base):
    __tablename__ = "instruction_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    instruction_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("strategy_instructions.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt_content: Mapped[str] = mapped_column(Text, nullable=False)
    change_summary: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    instruction = relationship("StrategyInstruction", back_populates="versions")

    __table_args__ = (
        UniqueConstraint("instruction_id", "version", name="uq_instruction_version"),
    )

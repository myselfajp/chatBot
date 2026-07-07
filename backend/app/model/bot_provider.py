from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import String, Boolean, Integer, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class BotProvider(Base):
    """Per-bot configuration for a single LLM provider.

    One row per (bot, provider). The API key is stored encrypted at rest.
    """

    __tablename__ = "bot_providers"
    __table_args__ = (
        UniqueConstraint("bot_id", "provider", name="uq_bot_provider"),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, nullable=False
    )
    bot_id: Mapped[int] = mapped_column(
        ForeignKey("bots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # "openai" | "anthropic" | "deepseek"
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Free-form model string the customer types (e.g. "gpt-4o-mini").
    model: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    # Fernet-encrypted API key. Empty string means "not set".
    api_key_encrypted: Mapped[str] = mapped_column(Text, nullable=False, default="")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    bot = relationship("Bot", back_populates="providers")

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class FeedJob(Base):
    """A background job that builds feed data from a website's sitemap."""

    __tablename__ = "feed_jobs"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        nullable=False,
    )
    bot_id: Mapped[int] = mapped_column(
        ForeignKey("bots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sitemap_url: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    # queued | running | done | error
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued")
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    pages_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pages_done: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    items_added: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

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

    bot = relationship("Bot")

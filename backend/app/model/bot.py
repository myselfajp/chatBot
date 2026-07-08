from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _gen_public_key() -> str:
    """Public identifier used by the embeddable widget (safe to expose)."""
    return uuid.uuid4().hex


class Bot(Base):
    """A chatbot configuration owned by a customer, embeddable on a website."""

    __tablename__ = "bots"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, nullable=False
    )
    # Public, non-secret key placed in the embed snippet (data-bot-key).
    public_key: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False, default=_gen_public_key
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    # Main site domain / URL, e.g. https://example.com
    site_url: Mapped[str] = mapped_column(String(500), nullable=False, default="")

    # Display rules for where the widget appears:
    #   "all"        -> show on every page
    #   "all_except" -> show everywhere EXCEPT the listed paths/URLs
    #   "only"       -> show ONLY on the listed paths/URLs
    display_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="all")
    # Newline-separated list of paths or URLs used by all_except / only modes.
    display_paths: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # The system prompt: rules, tone, persona.
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # Source ("feed") data the bot answers from instead of crawling the site.
    feed_data: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Which configured provider to use: "openai" | "anthropic" | "deepseek"
    active_provider: Mapped[str] = mapped_column(
        String(20), nullable=False, default="openai"
    )

    # Widget appearance
    widget_title: Mapped[str] = mapped_column(
        String(120), nullable=False, default="Assistant"
    )
    # Small role line under the name in the header, e.g. "Product Specialist".
    bot_subtitle: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    # URL of the avatar/logo image shown in the header (configured in the panel).
    logo_url: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    welcome_message: Mapped[str] = mapped_column(
        Text, nullable=False, default="Hi! How can I help you today?"
    )
    # Newline-separated quick-reply buttons shown above the input.
    quick_replies: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # JSON array of link buttons [{"text": "...", "slug": "/contact"}] shown in
    # both the compact and full widget; clicking navigates to the slug.
    link_buttons: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # Optional small disclaimer shown under the input.
    footer_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    accent_color: Mapped[str] = mapped_column(
        String(20), nullable=False, default="#4f46e5"
    )
    # Collapsed launcher style: "circle" (round button), "icon" (custom image),
    # or "bar" (a compact chat box with an expand button).
    launcher_style: Mapped[str] = mapped_column(
        String(20), nullable=False, default="circle"
    )
    # Custom launcher image URL, used when launcher_style == "icon".
    launcher_icon_url: Mapped[str] = mapped_column(
        String(500), nullable=False, default=""
    )
    # Admin-authored custom CSS / JS applied to the widget (override our styles).
    custom_css: Mapped[str] = mapped_column(Text, nullable=False, default="")
    custom_js: Mapped[str] = mapped_column(Text, nullable=False, default="")

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

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

    # Relationships
    user = relationship("User", back_populates="bots")
    providers = relationship(
        "BotProvider",
        back_populates="bot",
        cascade="all, delete-orphan",
    )
    conversations = relationship(
        "Conversation",
        back_populates="bot",
        cascade="all, delete-orphan",
    )

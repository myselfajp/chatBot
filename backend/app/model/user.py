from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Boolean, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, nullable=False
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    is_email_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    is_two_factor_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    failed_login_attempts: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    last_failed_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    login_otps = relationship(
        "LoginOTP",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    email_verification_tokens = relationship(
        "EmailVerificationToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    password_reset_tokens = relationship(
        "PasswordResetToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # Relationship to owned chatbots
    bots = relationship(
        "Bot",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def is_customer(self) -> bool:
        return self.role == "customer"

    def is_admin(self) -> bool:
        return self.role == "admin"

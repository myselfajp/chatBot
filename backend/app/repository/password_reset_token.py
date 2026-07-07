from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.model.password_reset_token import PasswordResetToken
from .base import BaseRepository


class PasswordResetTokenRepository(BaseRepository[PasswordResetToken]):
    def __init__(self):
        super().__init__(PasswordResetToken, resource_name="PasswordResetToken")

    def create_token(
        self,
        db: Session,
        user_id: int,
        token: str,
        expires_at: datetime,
    ) -> PasswordResetToken:
        reset_token = PasswordResetToken(
            user_id=user_id, token=token, expires_at=expires_at
        )
        db.add(reset_token)
        db.commit()
        db.refresh(reset_token)
        return reset_token

    def get_by_token(self, db: Session, token: str) -> Optional[PasswordResetToken]:
        stmt = select(PasswordResetToken).where(PasswordResetToken.token == token)
        return db.execute(stmt).scalar_one_or_none()

    def mark_as_used(self, db: Session, reset_token: PasswordResetToken) -> PasswordResetToken:
        reset_token.used_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(reset_token)
        return reset_token

    def purge_expired_tokens(self, db: Session) -> None:
        """Delete expired tokens"""
        now = datetime.now(timezone.utc)
        stmt = delete(PasswordResetToken).where(PasswordResetToken.expires_at < now)
        db.execute(stmt)
        db.commit()

    def purge_tokens_for_user(self, db: Session, user_id: int) -> None:
        """Delete all tokens for a user"""
        stmt = delete(PasswordResetToken).where(PasswordResetToken.user_id == user_id)
        db.execute(stmt)
        db.commit()

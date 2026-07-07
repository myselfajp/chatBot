from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.model.email_verification_token import EmailVerificationToken
from .base import BaseRepository


class EmailVerificationTokenRepository(BaseRepository[EmailVerificationToken]):
    def __init__(self):
        super().__init__(EmailVerificationToken, resource_name="EmailVerificationToken")

    def create_token(
        self,
        db: Session,
        user_id: int,
        token: str,
        expires_at: datetime,
    ) -> EmailVerificationToken:
        verification_token = EmailVerificationToken(
            user_id=user_id, token=token, expires_at=expires_at
        )
        db.add(verification_token)
        db.commit()
        db.refresh(verification_token)
        return verification_token

    def get_by_token(self, db: Session, token: str) -> Optional[EmailVerificationToken]:
        stmt = select(EmailVerificationToken).where(EmailVerificationToken.token == token)
        return db.execute(stmt).scalar_one_or_none()

    def mark_as_used(self, db: Session, verification_token: EmailVerificationToken) -> EmailVerificationToken:
        verification_token.used_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(verification_token)
        return verification_token

    def purge_expired_tokens(self, db: Session) -> None:
        """Delete expired tokens"""
        now = datetime.now(timezone.utc)
        stmt = delete(EmailVerificationToken).where(EmailVerificationToken.expires_at < now)
        db.execute(stmt)
        db.commit()

    def purge_tokens_for_user(self, db: Session, user_id: int) -> None:
        """Delete all tokens for a user (used when email is verified)"""
        stmt = delete(EmailVerificationToken).where(EmailVerificationToken.user_id == user_id)
        db.execute(stmt)
        db.commit()

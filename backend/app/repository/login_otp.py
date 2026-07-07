from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.model.login_otp import LoginOTP
from .base import BaseRepository


class LoginOTPRepository(BaseRepository[LoginOTP]):
    def __init__(self):
        super().__init__(LoginOTP, resource_name="LoginOTP")

    def create_challenge(
        self,
        db: Session,
        user_id: int,
        code_hash: str,
        expires_at: datetime,
    ) -> LoginOTP:
        otp = LoginOTP(user_id=user_id, code_hash=code_hash, expires_at=expires_at)
        db.add(otp)
        db.commit()
        db.refresh(otp)
        return otp

    def get_by_id(self, db: Session, otp_id: str) -> Optional[LoginOTP]:
        stmt = select(LoginOTP).where(LoginOTP.id == otp_id)
        return db.execute(stmt).scalar_one_or_none()

    def consume(self, db: Session, otp: LoginOTP) -> LoginOTP:
        otp.consumed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(otp)
        return otp

    def purge_pending_for_user(self, db: Session, user_id: int) -> None:
        stmt = (
            delete(LoginOTP)
            .where(LoginOTP.user_id == user_id)
            .where(LoginOTP.consumed_at.is_(None))
        )
        db.execute(stmt)
        db.commit()

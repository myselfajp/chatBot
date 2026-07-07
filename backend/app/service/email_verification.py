import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.repository.email_verification_token import EmailVerificationTokenRepository
from app.repository.user import UserRepository
from app.service.user import UserService


class EmailVerificationService:
    def __init__(
        self,
        token_repo: Optional[EmailVerificationTokenRepository] = None,
        user_repo: Optional[UserRepository] = None,
        user_service: Optional[UserService] = None,
    ):
        self.token_repo = token_repo or EmailVerificationTokenRepository()
        self.user_repo = user_repo or UserRepository()
        self.user_service = user_service or UserService()

    def create_verification_token(self, db: Session, user_id: int) -> str:
        """
        Create a new email verification token for a user.

        Args:
            db: Database session
            user_id: ID of the user

        Returns:
            Verification token string
        """
        # Generate a secure token
        token = secrets.token_urlsafe(32)

        # Calculate expiration time
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.EMAIL_VERIFICATION_TOKEN_EXPIRATION_MINUTES
        )

        # Create token record
        self.token_repo.create_token(
            db=db,
            user_id=user_id,
            token=token,
            expires_at=expires_at,
        )

        return token

    def verify_token(self, db: Session, token: str) -> int:
        """
        Verify an email verification token and return user_id.

        Args:
            db: Database session
            token: Verification token

        Returns:
            User ID if token is valid

        Raises:
            HTTPException: If token is invalid, expired, or already used
        """
        # Get token from database
        verification_token = self.token_repo.get_by_token(db, token)

        if not verification_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification token.",
            )

        # Check if token has already been used
        if verification_token.used_at is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This verification token has already been used.",
            )

        # Check if token has expired
        now = datetime.now(timezone.utc)
        if verification_token.expires_at < now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification token has expired. Please request a new verification email.",
            )

        # Mark token as used
        self.token_repo.mark_as_used(db, verification_token)

        # Verify user's email
        user = self.user_service.verify_email(db, verification_token.user_id)

        # Clean up all tokens for this user (they're verified now)
        self.token_repo.purge_tokens_for_user(db, verification_token.user_id)

        return user.id

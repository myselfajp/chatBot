import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.repository.password_reset_token import PasswordResetTokenRepository
from app.repository.user import UserRepository


class PasswordResetService:
    def __init__(
        self,
        token_repo: Optional[PasswordResetTokenRepository] = None,
        user_repo: Optional[UserRepository] = None,
    ):
        self.token_repo = token_repo or PasswordResetTokenRepository()
        self.user_repo = user_repo or UserRepository()

    def create_reset_token(self, db: Session, email: str) -> Optional[str]:
        """
        Create a password reset token for a user by email.

        Args:
            db: Database session
            email: User's email address

        Returns:
            Reset token string if user exists, None otherwise
            (Returns None to prevent email enumeration attacks)
        """
        # Get user by email
        user = self.user_repo.get_by_email(db, email)

        # Always return success to prevent email enumeration
        # If user doesn't exist, we still return None but don't raise error
        if not user:
            return None

        # Generate a secure token
        token = secrets.token_urlsafe(32)

        # Calculate expiration time
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.PASSWORD_RESET_TOKEN_EXPIRATION_MINUTES
        )

        # Purge old tokens for this user
        self.token_repo.purge_tokens_for_user(db, user.id)

        # Create token record
        self.token_repo.create_token(
            db=db,
            user_id=user.id,
            token=token,
            expires_at=expires_at,
        )

        return token

    def reset_password(self, db: Session, token: str, new_password: str) -> int:
        """
        Reset user's password using a reset token.

        Args:
            db: Database session
            token: Password reset token
            new_password: New password to set

        Returns:
            User ID if password reset is successful

        Raises:
            HTTPException: If token is invalid, expired, or already used
        """
        # Get token from database
        reset_token = self.token_repo.get_by_token(db, token)

        if not reset_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset token.",
            )

        # Check if token has already been used
        if reset_token.used_at is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This reset token has already been used.",
            )

        # Check if token has expired
        now = datetime.now(timezone.utc)
        if reset_token.expires_at < now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has expired. Please request a new password reset.",
            )

        # Get user
        user = self.user_repo.get(db, reset_token.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        # Hash new password
        hashed_password = hash_password(new_password)

        # Update user password
        update_data = {"password_hash": hashed_password}
        self.user_repo.update_user(db, user, update_data)

        # Mark token as used
        self.token_repo.mark_as_used(db, reset_token)

        # Clean up all tokens for this user
        self.token_repo.purge_tokens_for_user(db, user.id)

        return user.id

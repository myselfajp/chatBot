from fastapi import Depends, HTTPException, status, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from typing import Optional
from app.service.auth import AuthService
from app.service.user import UserService
from app.service.email_verification import EmailVerificationService
from app.service.password_reset import PasswordResetService
from app.service.bot import BotService
from app.core.config import settings
from app.db.session import get_db
from app.repository.user import UserRepository
from app.model.user import User


def get_auth_service() -> AuthService:
    return AuthService()


def get_user_service() -> UserService:
    return UserService()


def get_email_verification_service() -> EmailVerificationService:
    return EmailVerificationService()


def get_password_reset_service() -> PasswordResetService:
    return PasswordResetService()


def get_bot_service() -> BotService:
    return BotService()


security_scheme = HTTPBearer(auto_error=False)


def get_token_from_header(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
) -> str:
    """
    Extract JWT token using HTTP Bearer auth for proper Swagger support.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if (credentials.scheme or "").lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token


def get_current_user(
    token: str = Depends(get_token_from_header),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency to get the current authenticated user from JWT token
    """
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_repo = UserRepository()
    user = user_repo.get_by_email(db, email=email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Dependency to verify the current user is an administrator
    """
    if not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Admin privileges required",
        )
    return current_user

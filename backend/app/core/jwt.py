from datetime import datetime, timedelta, timezone
from jose import jwt
from app.core.config import settings


def create_access_token(subject: str, expires_minutes: int = None) -> str:
    # Default to 1 day (1440 minutes) if not specified
    minutes = expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    expire = datetime.now(tz=timezone.utc) + timedelta(minutes=minutes)
    to_encode = {"sub": subject, "exp": expire}
    return jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )

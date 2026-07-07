from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.security import hash_password
from app.repository.user import UserRepository


def ensure_initial_admin(db: Session) -> None:
    """Create first admin if not exist"""
    if not settings.CREATE_ADMIN_ON_STARTUP:
        return

    repo = UserRepository()

    if repo.get_by_email(db, settings.ADMIN_EMAIL):
        return

    repo.create(
        db,
        {
            "email": settings.ADMIN_EMAIL,
            "password_hash": hash_password(settings.ADMIN_PASSWORD),
            "role": "admin",
            "full_name": "System Administrator",
            "phone_number": "",
            "is_active": True,
            "is_email_verified": True,  # Admin email is auto-verified
            "is_two_factor_enabled": False,
        },
    )
    print(f"[seed] Admin user created: {settings.ADMIN_EMAIL}")

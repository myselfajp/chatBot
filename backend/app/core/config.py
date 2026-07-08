from functools import lru_cache
from typing import Optional
from urllib.parse import quote_plus
from pydantic_settings import BaseSettings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # Project Configuration
    PROJECT_NAME: str
    API_V1_PREFIX: str

    # JWT Configuration
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # Database Configuration
    # If DATABASE_URL is not provided, it will be constructed from individual components
    DATABASE_URL: Optional[str] = None
    
    # Database components (used to build DATABASE_URL if not provided)
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str

    # Admin User Configuration
    CREATE_ADMIN_ON_STARTUP: bool
    ADMIN_EMAIL: str
    ADMIN_PASSWORD: str

    # CORS Configuration
    CORS_ORIGINS: str

    # Email Provider Configuration
    EMAIL_PROVIDER: str  # Options: "aws_ses" or "smtp"
    SENDER_EMAIL: str  # Email address to send from (used by both providers)

    # AWS SES configuration (required if EMAIL_PROVIDER=aws_ses)
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_SES_REGION: str

    # SMTP configuration (required if EMAIL_PROVIDER=smtp)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_USE_TLS: bool
    SMTP_USE_SSL: bool

    # OTP configuration
    OTP_LENGTH: int
    OTP_EXPIRATION_MINUTES: int

    # Email verification configuration
    EMAIL_VERIFICATION_TOKEN_EXPIRATION_MINUTES: int
    REQUIRE_EMAIL_VERIFICATION: bool  # If True, check email verification on login

    # Password reset configuration
    PASSWORD_RESET_TOKEN_EXPIRATION_MINUTES: int

    # Two-factor authentication configuration
    FORCE_TWO_FACTOR_AUTH: bool  # If True, 2FA is required for all users regardless of is_two_factor_enabled

    # Site configuration
    BASE_URL: str
    # Frontend / panel URL (used to build links in emails, e.g. email verification)
    FRONTEND_URL: str = "http://localhost:5173"

    # Encryption key used to encrypt provider API keys at rest.
    # Must be a URL-safe base64-encoded 32-byte key (Fernet key).
    # Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    ENCRYPTION_KEY: str

    # Maximum number of characters of a bot's feed data injected into the LLM context.
    FEED_DATA_MAX_CHARS: int = 20000
    # Number of previous messages loaded as conversation context.
    CHAT_HISTORY_LIMIT: int = 20

    # Celery / background jobs
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_TASK_ALWAYS_EAGER: bool = False

    # Limits for admin-authored custom widget CSS / JS.
    CUSTOM_CSS_MAX_CHARS: int = 20000
    CUSTOM_JS_MAX_CHARS: int = 20000

    class Config:
        env_file = ".env"
        extra = "ignore"


def _build_database_url(
    host: str,
    port: int,
    db: str,
    user: str,
    password: str,
) -> str:
    """Build DATABASE_URL from individual components (credentials URL-encoded)."""
    return (
        f"postgresql://{quote_plus(user)}:{quote_plus(password)}"
        f"@{host}:{port}/{db}"
    )


@lru_cache
def get_settings():
    try:
        # Pydantic BaseSettings loads values from environment; the constructor
        # appears to require all fields to be passed in by static analyzers.
        # At runtime, no args are needed. Silence the type checker accordingly.
        settings = Settings()  # type: ignore[call-arg]
        
        # Build DATABASE_URL if not provided
        if not settings.DATABASE_URL:
            settings.DATABASE_URL = _build_database_url(
                host=settings.POSTGRES_HOST,
                port=settings.POSTGRES_PORT,
                db=settings.POSTGRES_DB,
                user=settings.POSTGRES_USER,
                password=settings.POSTGRES_PASSWORD,
            )
            logger.info("DATABASE_URL was automatically constructed from database components")
        
    except Exception as e:
        logger.error(f"Failed to load settings: {e}")
        logger.error(
            "Failed to load environment variables. Please ensure all required settings are defined in your environment or .env file. Check for missing or incorrectly named variables."
        )
        raise

    logger.info(f"Loading settings from environment: {settings.Config.env_file}")
    return settings


settings = get_settings()

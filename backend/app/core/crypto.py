"""Symmetric encryption for provider API keys stored at rest.

Keys are encrypted with Fernet using ``settings.ENCRYPTION_KEY``. Plaintext keys
never leave the server: the API only ever returns a masked hint (last 4 chars).
"""
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


@lru_cache
def _fernet() -> Fernet:
    key = settings.ENCRYPTION_KEY
    if isinstance(key, str):
        key = key.encode("utf-8")
    return Fernet(key)


def encrypt(plaintext: str) -> str:
    """Encrypt a secret. Returns "" for empty input."""
    if not plaintext:
        return ""
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt(token: str) -> str:
    """Decrypt a stored secret. Returns "" for empty/invalid input."""
    if not token:
        return ""
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        return ""


def mask_key(token: str) -> str:
    """Return a non-reversible hint for a stored (encrypted) key, e.g. '••••abcd'."""
    plain = decrypt(token)
    if not plain:
        return ""
    if len(plain) <= 4:
        return "••••"
    return "••••" + plain[-4:]

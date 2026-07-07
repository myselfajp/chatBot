import bcrypt


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password to hash

    Returns:
        Hashed password as a string

    Raises:
        TypeError: If password is not a string or bytes
    """
    if not isinstance(password, (str, bytes)):
        raise TypeError("Password must be str or bytes")

    byte_pass = password.encode("utf-8") if isinstance(password, str) else password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(byte_pass, salt)

    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        byte_plain = plain.encode("utf-8")
        byte_hashed = hashed.encode("utf-8")
        return bcrypt.checkpw(byte_plain, byte_hashed)
    except (ValueError, AttributeError):
        return False

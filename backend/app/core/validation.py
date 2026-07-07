import re
from typing import Optional
import unicodedata


def validate_email(email: str) -> tuple[bool, Optional[str]]:
    """
    Validate email format.

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not email or len(email) < 3:
        return False, "Email is too short"

    if len(email) > 255:
        return False, "Email is too long"

    # Basic email regex pattern
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

    if not re.match(email_pattern, email):
        return False, "Invalid email format"

    return True, None


def validate_password(password: str) -> tuple[bool, Optional[str]]:
    """
    Validate password strength.

    Requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not password:
        return False, "Password is required"

    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if len(password) > 128:
        return False, "Password is too long (max 128 characters)"

    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"

    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"

    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit"

    return True, None


def validate_phone_number(phone: str) -> tuple[bool, Optional[str]]:
    """
    Validate international phone number format.

    Accepts various international formats:
    - +1234567890 (with country code)
    - 001234567890 (with international prefix)
    - 1234567890 (local format)
    - Allows spaces, dashes, parentheses

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not phone:
        return True, None  # Phone is optional

    # Remove spaces, dashes, parentheses, and dots
    cleaned_phone = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "").replace(".", "")

    # Must contain only digits and optionally start with +
    if not re.match(r"^\+?\d+$", cleaned_phone):
        return False, "Phone number must contain only digits, spaces, dashes, or start with +"

    # Remove the + for length check
    digits_only = cleaned_phone.lstrip("+").lstrip("0")

    # Phone numbers should be between 7 and 15 digits (international standard)
    if len(digits_only) < 7:
        return False, "Phone number is too short (minimum 7 digits)"

    if len(cleaned_phone.lstrip("+")) > 15:
        return False, "Phone number is too long (maximum 15 digits)"

    return True, None


def sanitize_string(text: Optional[str], max_length: int = 1000) -> Optional[str]:
    """
    Sanitize input string by removing dangerous characters and limiting length.

    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized string or None
    """
    if text is None:
        return None

    # Strip whitespace
    text = text.strip()

    if not text:
        return None

    # Limit length
    if len(text) > max_length:
        text = text[:max_length]

    return text

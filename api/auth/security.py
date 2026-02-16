"""Security utilities for password hashing and JWT handling."""

from datetime import datetime, timedelta, timezone

import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

from api.config import Settings

# Password hashing using Argon2 (recommended algorithm)
password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Hash a password using Argon2.

    Args:
        password: Plain text password to hash

    Returns:
        Argon2 hash string
    """
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Argon2 hash to verify against

    Returns:
        True if password matches, False otherwise
    """
    return password_hash.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token.

    Args:
        data: Payload data to encode in the token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT string
    """
    settings = Settings()
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and verify a JWT access token.

    Args:
        token: JWT string to decode

    Returns:
        Decoded payload dictionary

    Raises:
        jwt.exceptions.InvalidTokenError: If token is invalid or expired
    """
    settings = Settings()
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


def create_reset_token(email: str) -> str:
    """Create a short-lived token for password reset (15 min expiry).

    Args:
        email: User email address to encode in token

    Returns:
        Encoded JWT string with type=reset and 15-minute expiry
    """
    settings = Settings()
    return jwt.encode(
        {
            "sub": email,
            "type": "reset",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
        },
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

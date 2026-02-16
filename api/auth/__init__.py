"""Authentication module for CFU-Counter API."""

from api.auth.dependencies import get_current_user
from api.auth.schemas import MessageResponse, UserCreate, UserLogin, UserResponse
from api.auth.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

__all__ = [
    # Security utilities
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_access_token",
    # Dependencies
    "get_current_user",
    # Schemas
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "MessageResponse",
]

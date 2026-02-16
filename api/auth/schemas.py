"""Pydantic schemas for authentication requests and responses."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for user registration."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class UserLogin(BaseModel):
    """Schema for user login (alternative to OAuth2PasswordRequestForm)."""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Schema for user data in responses (excludes password)."""

    id: int
    email: str
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str


class ForgotPasswordRequest(BaseModel):
    """Schema for password reset request."""

    email: EmailStr


class PasswordResetRequest(BaseModel):
    """Schema for password reset completion."""

    token: str
    new_password: str = Field(..., min_length=8, max_length=128)

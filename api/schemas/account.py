"""Pydantic schemas for account settings."""

from pydantic import BaseModel, Field


class PasswordChangeRequest(BaseModel):
    """Request body for changing password."""

    current_password: str = Field(..., description="Current password for verification")
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password (8-128 characters)",
    )

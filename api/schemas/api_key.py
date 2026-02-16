"""Pydantic schemas for API key management."""

from datetime import datetime

from pydantic import BaseModel, Field


class APIKeyCreate(BaseModel):
    """Request body for creating an API key."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Human-readable name for the API key",
    )


class APIKeyResponse(BaseModel):
    """Response for an API key (without the full key)."""

    id: int
    name: str
    prefix: str = Field(..., description="First 12 characters of the key")
    is_active: bool
    last_used_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class APIKeyCreated(APIKeyResponse):
    """Response when creating an API key (includes full key, shown only once)."""

    key: str = Field(..., description="Full API key - store securely, shown only once")

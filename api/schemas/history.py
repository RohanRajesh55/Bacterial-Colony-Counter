"""Pydantic schemas for prediction history."""

from datetime import datetime

from pydantic import BaseModel, Field


class PredictionHistoryItem(BaseModel):
    """Schema for a prediction history item."""

    id: int
    colony_count: int = Field(serialization_alias="total_count")
    confidence_threshold: float
    model_used: str = Field(serialization_alias="model_type")
    created_at: datetime
    # S3 keys from DB (excluded from serialization, used to generate URLs)
    original_image_key: str = Field(exclude=True)
    annotated_image_key: str | None = Field(default=None, exclude=True)
    # Presigned URLs (computed after pagination)
    original_image_url: str | None = None
    annotated_image_url: str | None = None

    model_config = {"from_attributes": True, "populate_by_name": True}

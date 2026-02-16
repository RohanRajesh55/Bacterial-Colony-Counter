"""Pydantic models for API request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class Detection(BaseModel):
    """Individual colony detection with bounding box and confidence."""

    box: list[float] = Field(
        ..., description="Bounding box coordinates [x1, y1, x2, y2] in pixels"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence score")

    model_config = {
        "json_schema_extra": {
            "examples": [{"box": [100.5, 200.3, 150.2, 250.8], "confidence": 0.92}]
        }
    }


class ClassCount(BaseModel):
    """Count of colonies for a specific bacterial class."""

    name: str = Field(..., description="Bacterial species name")
    count: int = Field(..., ge=0, description="Number of colonies detected")

    model_config = {
        "json_schema_extra": {
            "examples": [{"name": "E.coli", "count": 25}]
        }
    }


class PredictionResponse(BaseModel):
    """Response from colony prediction endpoint."""

    total_count: int = Field(..., ge=0, description="Total number of colonies detected")
    class_counts: list[ClassCount] = Field(
        default_factory=list, description="Breakdown by bacterial class"
    )
    model_used: str = Field(..., description="Model that performed detection")
    detections: list[Detection] = Field(
        default_factory=list, description="Individual detection boxes with coordinates and confidence"
    )
    processed_image: str | None = Field(
        None, description="Base64 encoded processed image"
    )
    annotated_image: str | None = Field(
        None, description="Base64 encoded image with bounding boxes"
    )
    prediction_id: int | None = Field(
        None, description="Database ID of saved prediction"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "total_count": 42,
                    "class_counts": [
                        {"name": "E.coli", "count": 25},
                        {"name": "S.aureus", "count": 17},
                    ],
                    "model_used": "rtdetr",
                    "processed_image": "data:image/png;base64,...",
                    "annotated_image": "data:image/png;base64,...",
                    "prediction_id": 1,
                }
            ]
        }
    }


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Service status")

    model_config = {
        "json_schema_extra": {
            "examples": [{"status": "healthy"}]
        }
    }


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str = Field(..., description="Error message")

    model_config = {
        "json_schema_extra": {
            "examples": [{"detail": "Only JPEG and PNG images are accepted"}]
        }
    }


class FeedbackCreate(BaseModel):
    """Request body for creating user feedback on a prediction."""

    prediction_id: int = Field(..., description="ID of the prediction being corrected")
    actual_count: int = Field(..., ge=0, description="User-reported actual colony count")
    comments: str | None = Field(
        None, max_length=500, description="Optional feedback notes"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "prediction_id": 1,
                    "actual_count": 42,
                    "comments": "Counted manually under microscope",
                }
            ]
        }
    }


class FeedbackResponse(BaseModel):
    """Response after creating feedback."""

    id: int = Field(..., description="Unique feedback ID")
    prediction_id: int = Field(..., description="Associated prediction ID")
    actual_count: int = Field(..., ge=0, description="User-reported actual colony count")
    comments: str | None = Field(None, description="Optional feedback notes")
    created_at: datetime = Field(..., description="Timestamp of feedback creation")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "prediction_id": 1,
                    "actual_count": 42,
                    "comments": "Counted manually under microscope",
                    "created_at": "2026-01-25T12:00:00Z",
                }
            ]
        },
    }


class CorrectionAction(BaseModel):
    """Single correction action on a detection."""

    action_type: str = Field(..., description="Type of correction: add, remove, adjust, split")
    box: list[float] | None = Field(
        None, description="Corrected box [x1, y1, x2, y2] in pixels (null for remove)"
    )
    original_box: list[float] | None = Field(
        None, description="Original box before adjustment (null for add)"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "action_type": "adjust",
                    "box": [110.0, 210.0, 160.0, 260.0],
                    "original_box": [100.0, 200.0, 150.0, 250.0],
                }
            ]
        }
    }


class CorrectionCreate(BaseModel):
    """Request body for creating corrections on a prediction."""

    prediction_id: int = Field(..., description="ID of the prediction being corrected")
    actions: list[CorrectionAction] = Field(
        ..., description="List of correction actions to apply"
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "prediction_id": 1,
                    "actions": [
                        {
                            "action_type": "add",
                            "box": [50.0, 50.0, 100.0, 100.0],
                            "original_box": None,
                        },
                        {
                            "action_type": "remove",
                            "box": None,
                            "original_box": [200.0, 200.0, 250.0, 250.0],
                        },
                    ],
                }
            ]
        }
    }


class CorrectionSummary(BaseModel):
    """Summary of corrections applied to a prediction."""

    added: int = Field(default=0, description="Number of detections added")
    removed: int = Field(default=0, description="Number of detections removed")
    adjusted: int = Field(default=0, description="Number of detections adjusted")
    split: int = Field(default=0, description="Number of detections split")
    corrected_count: int = Field(..., description="Final colony count after corrections")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "added": 2,
                    "removed": 1,
                    "adjusted": 3,
                    "split": 0,
                    "corrected_count": 45,
                }
            ]
        }
    }


class CorrectionResponse(BaseModel):
    """Response after saving corrections."""

    id: int = Field(..., description="ID of the first correction saved")
    prediction_id: int = Field(..., description="Associated prediction ID")
    corrected_count: int = Field(..., description="Final colony count after corrections")
    created_at: datetime = Field(..., description="Timestamp of correction")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "prediction_id": 1,
                    "corrected_count": 45,
                    "created_at": "2026-02-15T12:00:00Z",
                }
            ]
        },
    }

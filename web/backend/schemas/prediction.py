"""
Pydantic schemas for prediction API requests and responses.
"""
from pydantic import BaseModel, Field
from typing import Optional


class ClassCount(BaseModel):
    """Count of colonies for a specific class."""
    name: str = Field(..., description="Bacterial class name")
    count: int = Field(..., description="Number of colonies detected")
    confidence: Optional[float] = Field(None, description="Average confidence (YOLO only)")


    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "model_used": "yolo",
                "total_count": 47,
                "class_counts": [
                    {"name": "E.coli", "count": 25, "confidence": 0.89},
                    {"name": "B.subtilis", "count": 22, "confidence": 0.85}
                ],
                "processed_image": "base64...",
                "annotated_image": "base64...",
                "detections": [
                    {"x": 100, "y": 200, "w": 50, "h": 50, "label": "E.coli", "confidence": 0.9}
                ]
            }
        }

class Detection(BaseModel):
    """Single colony detection data."""
    x: int
    y: int
    w: int
    h: int
    label: str
    confidence: float

class PredictionResponse(BaseModel):
    """Response schema for prediction endpoint."""
    success: bool = Field(..., description="Whether prediction succeeded")
    analysis_id: Optional[int] = Field(None, description="Database ID of the analysis")
    model_used: str = Field(..., description="Model type used: 'cnn' or 'yolo'")

    total_count: int = Field(..., description="Total number of colonies detected")
    class_counts: list[ClassCount] = Field(..., description="Breakdown by class")
    processed_image: str = Field(..., description="Base64 encoded processed image")
    annotated_image: Optional[str] = Field(None, description="Base64 image with bounding boxes (YOLO only)")
    heatmap_image: Optional[str] = Field(None, description="Base64 heatmap overlay (YOLO only)")
    
    # New field for client-side rendering
    detections: Optional[list[Detection]] = Field(None, description="List of bounding boxes (YOLO only)")
    
    error: Optional[str] = Field(None, description="Error message if failed")

"""Colony prediction endpoint."""

import asyncio
import base64
import logging
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from api import state
from api.auth.dependencies import get_optional_user
from api.config import Settings
from api.db.models import Prediction, User
from api.db.session import get_db
from api.schemas import Detection, ErrorResponse, PredictionResponse
from api.state import ml_models
from api.storage import compute_image_hash, get_extension_from_content_type, upload_image

logger = logging.getLogger(__name__)

router = APIRouter(tags=["prediction"])

# Thread pool for running sync inference in async context
executor = ThreadPoolExecutor(max_workers=2)


def _run_inference(
    image_bytes: bytes, confidence_threshold: float, show_boxes: bool
) -> dict:
    """Sync function that runs in thread pool.

    Args:
        image_bytes: Raw image bytes
        confidence_threshold: Minimum detection confidence
        show_boxes: Whether to generate annotated image

    Returns:
        Dict with count, detections, and optionally annotated_image
    """
    service = ml_models["rtdetr"]

    # Load image from bytes
    image = Image.open(BytesIO(image_bytes))
    if image.mode != "RGB":
        image = image.convert("RGB")

    # Run detection
    count, detections = service.predict(image, confidence_threshold)

    # Generate annotated image if requested
    annotated_b64 = None
    if show_boxes and detections:
        annotated = service.annotate_image(image, detections)
        annotated_b64 = service.image_to_base64(annotated)

    return {
        "count": count,
        "detections": detections,
        "annotated_image": annotated_b64,
    }


async def run_inference_with_timeout(
    image_bytes: bytes,
    confidence_threshold: float,
    show_boxes: bool,
    timeout_seconds: float = 30.0,
) -> dict:
    """Run inference with timeout protection.

    Args:
        image_bytes: Raw image bytes
        confidence_threshold: Minimum detection confidence
        show_boxes: Whether to generate annotated image
        timeout_seconds: Maximum time for inference (default 30s)

    Returns:
        Dict with count, detections, and optionally annotated_image

    Raises:
        HTTPException: 504 if inference times out
    """
    loop = asyncio.get_event_loop()
    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(
                executor,
                _run_inference,
                image_bytes,
                confidence_threshold,
                show_boxes,
            ),
            timeout=timeout_seconds,
        )
        return result
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail=f"Inference timed out after {timeout_seconds} seconds",
        )


@router.post(
    "/predict",
    response_model=PredictionResponse,
    responses={400: {"model": ErrorResponse}},
)
@state.limiter.limit("10/minute")
async def predict_colonies(
    request: Request,
    image: Annotated[UploadFile, File(description="Petri dish image (JPEG or PNG)")],
    model_type: Annotated[str, Form(description="Model to use for prediction")] = "rtdetr",
    show_boxes: Annotated[str, Form(description="Whether to draw bounding boxes")] = "true",
    confidence_threshold: Annotated[str, Form(description="Confidence threshold")] = "0.40",
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> PredictionResponse:
    """
    Analyze a petri dish image and count bacterial colonies.

    Accepts multipart form data with an image file and optional parameters.
    Returns colony count and optionally an annotated image with bounding boxes.

    Note: show_boxes arrives as string "true" or "false" from HTML forms.
    Convert with `show_boxes.lower() == "true"` when needed for model inference.
    """
    # Check if model is loaded
    if "rtdetr" not in ml_models:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded. Server may still be starting up.",
        )

    # Load settings (inside function to avoid import-time validation errors)
    settings = Settings()

    # Validate content type
    if image.content_type not in settings.ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid image format. Accepted: {', '.join(sorted(settings.ALLOWED_CONTENT_TYPES))}",
        )

    # Validate file size (check before reading to avoid memory issues)
    if image.size and image.size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE // (1024 * 1024)}MB",
        )

    # Read image bytes
    contents = await image.read()

    # Compute image hash for storage key
    image_hash = compute_image_hash(contents)
    extension = get_extension_from_content_type(image.content_type or "image/png")

    # Parse form fields
    show_boxes_bool = show_boxes.lower() == "true"
    conf_threshold = float(confidence_threshold)

    # Run inference with timeout
    result = await run_inference_with_timeout(
        image_bytes=contents,
        confidence_threshold=conf_threshold,
        show_boxes=show_boxes_bool,
    )

    # Persist prediction to database and storage
    prediction_id = None
    try:
        # Upload original image to MinIO
        original_key = f"originals/{image_hash}.{extension}"
        upload_image(
            settings.S3_BUCKET_NAME, original_key, contents, image.content_type or "image/png"
        )

        # Upload annotated image if it exists
        annotated_key = None
        if result["annotated_image"]:
            # Annotated image is base64 with data URI prefix, decode it
            # Format: "data:image/png;base64,<base64_data>"
            b64_data = result["annotated_image"]
            if "," in b64_data:
                b64_data = b64_data.split(",", 1)[1]
            annotated_bytes = base64.b64decode(b64_data)
            annotated_key = f"annotated/{image_hash}.png"
            upload_image(settings.S3_BUCKET_NAME, annotated_key, annotated_bytes, "image/png")

        # Create prediction record in database
        prediction = Prediction(
            image_hash=image_hash,
            colony_count=result["count"],
            confidence_threshold=conf_threshold,
            model_used=model_type,
            original_image_key=original_key,
            annotated_image_key=annotated_key,
            user_id=current_user.id if current_user else None,
        )
        db.add(prediction)
        await db.commit()
        await db.refresh(prediction)
        prediction_id = prediction.id
        logger.info("Saved prediction %d for image %s", prediction_id, image_hash[:8])
    except Exception as e:
        # Log error but don't fail the request - inference still succeeded
        logger.error("Failed to persist prediction: %s", str(e))
        # Rollback any partial transaction
        await db.rollback()

    return PredictionResponse(
        total_count=result["count"],
        class_counts=[],  # Species classification deferred to v2
        model_used=model_type,
        detections=[
            Detection(box=d["box"], confidence=d["confidence"])
            for d in result["detections"]
        ],
        processed_image=None,
        annotated_image=result["annotated_image"],
        prediction_id=prediction_id,
    )

"""Router for prediction history endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_pagination import Page, add_pagination
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.dependencies import get_current_user
from api.config import Settings
from api.db.models import Prediction, User
from api.db.session import get_db
from api.schemas.history import PredictionHistoryItem
from api.storage.s3_client import get_presigned_url

router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_model=Page[PredictionHistoryItem])
async def get_prediction_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated prediction history for the current user.

    Args:
        current_user: Authenticated user from JWT cookie
        db: Async database session

    Returns:
        Paginated list of prediction history items with presigned URLs
    """
    settings = Settings()
    query = (
        select(Prediction)
        .where(Prediction.user_id == current_user.id)
        .order_by(Prediction.created_at.desc())
    )
    page = await paginate(db, query)

    # Transform items to add presigned URLs
    for item in page.items:
        item.original_image_url = get_presigned_url(
            settings.S3_BUCKET_NAME, item.original_image_key, expires_in=3600
        )
        item.annotated_image_url = (
            get_presigned_url(
                settings.S3_BUCKET_NAME, item.annotated_image_key, expires_in=3600
            )
            if item.annotated_image_key
            else None
        )

    return page


@router.get("/{prediction_id}", response_model=PredictionHistoryItem)
async def get_prediction_detail(
    prediction_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single prediction by ID.

    Args:
        prediction_id: ID of the prediction to retrieve
        current_user: Authenticated user from JWT cookie
        db: Async database session

    Returns:
        Prediction history item with presigned URLs

    Raises:
        HTTPException: 404 if prediction not found or not owned by user
    """
    settings = Settings()
    result = await db.execute(
        select(Prediction).where(
            Prediction.id == prediction_id, Prediction.user_id == current_user.id
        )
    )
    prediction = result.scalar_one_or_none()

    if prediction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prediction not found",
        )

    # Add presigned URLs
    prediction.original_image_url = get_presigned_url(
        settings.S3_BUCKET_NAME, prediction.original_image_key, expires_in=3600
    )
    prediction.annotated_image_url = (
        get_presigned_url(
            settings.S3_BUCKET_NAME, prediction.annotated_image_key, expires_in=3600
        )
        if prediction.annotated_image_key
        else None
    )

    return prediction

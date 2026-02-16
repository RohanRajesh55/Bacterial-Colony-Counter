"""Feedback router for user corrections on predictions."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.models import Feedback, Prediction
from api.db.session import get_db
from api.schemas import ErrorResponse, FeedbackCreate, FeedbackResponse

router = APIRouter(tags=["feedback"])


@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    responses={404: {"model": ErrorResponse}},
)
async def create_feedback(
    feedback: FeedbackCreate, db: AsyncSession = Depends(get_db)
) -> FeedbackResponse:
    """Create user feedback for a prediction.

    Allows users to submit the actual colony count when a prediction is incorrect,
    enabling future model improvement.

    Args:
        feedback: The feedback data including prediction_id and actual_count.
        db: Database session (injected by FastAPI).

    Returns:
        The created feedback record.

    Raises:
        HTTPException: 404 if the prediction_id does not exist.
    """
    # Verify prediction exists
    result = await db.execute(
        select(Prediction).where(Prediction.id == feedback.prediction_id)
    )
    prediction = result.scalar_one_or_none()

    if prediction is None:
        raise HTTPException(status_code=404, detail="Prediction not found")

    # Create feedback record
    feedback_record = Feedback(
        prediction_id=feedback.prediction_id,
        actual_count=feedback.actual_count,
        comments=feedback.comments,
    )
    db.add(feedback_record)
    await db.commit()
    await db.refresh(feedback_record)

    return feedback_record

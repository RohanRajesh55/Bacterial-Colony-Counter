"""Corrections endpoint for user edits on predictions."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.auth.dependencies import get_optional_user
from api.db.models import Correction, Prediction, User
from api.db.session import get_db
from api.schemas import CorrectionCreate, CorrectionResponse, CorrectionSummary

logger = logging.getLogger(__name__)

router = APIRouter(tags=["corrections"])


@router.post("/corrections", response_model=CorrectionResponse)
async def create_correction(
    correction_data: CorrectionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> CorrectionResponse:
    """
    Save user corrections for a prediction.

    Accepts a list of correction actions (add, remove, adjust, split) and persists them
    to track how the user modified the original detection results.
    """
    # Verify prediction exists
    result = await db.execute(
        select(Prediction).where(Prediction.id == correction_data.prediction_id)
    )
    prediction = result.scalar_one_or_none()

    if not prediction:
        raise HTTPException(status_code=404, detail="Prediction not found")

    # Create correction records for each action
    correction_records = []
    for action in correction_data.actions:
        correction = Correction(
            prediction_id=correction_data.prediction_id,
            action_type=action.action_type,
            box=action.box,
            original_box=action.original_box,
        )
        db.add(correction)
        correction_records.append(correction)

    await db.commit()

    # Refresh first correction to get its ID
    if correction_records:
        await db.refresh(correction_records[0])

    # Calculate corrected count
    # Start with original prediction count
    original_count = prediction.colony_count

    # Apply corrections
    added = sum(1 for a in correction_data.actions if a.action_type == "add")
    removed = sum(1 for a in correction_data.actions if a.action_type == "remove")
    split = sum(1 for a in correction_data.actions if a.action_type == "split")

    # Split creates one additional detection from the original
    corrected_count = original_count + added - removed + split

    user_id = current_user.id if current_user else None
    logger.info(
        "Saved %d corrections for prediction %d (user %s)",
        len(correction_records),
        correction_data.prediction_id,
        user_id,
    )

    return CorrectionResponse(
        id=correction_records[0].id if correction_records else 0,
        prediction_id=correction_data.prediction_id,
        corrected_count=corrected_count,
        created_at=correction_records[0].created_at if correction_records else datetime.now(timezone.utc),
    )


@router.get("/corrections/{prediction_id}", response_model=CorrectionSummary)
async def get_corrections(
    prediction_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> CorrectionSummary:
    """
    Get correction summary for a prediction.

    Returns counts of each correction type and the final corrected colony count.
    """
    # Verify prediction exists
    result = await db.execute(select(Prediction).where(Prediction.id == prediction_id))
    prediction = result.scalar_one_or_none()

    if not prediction:
        raise HTTPException(status_code=404, detail="Prediction not found")

    # Fetch all corrections for this prediction
    result = await db.execute(
        select(Correction).where(Correction.prediction_id == prediction_id)
    )
    corrections = result.scalars().all()

    # Count by action type
    added = sum(1 for c in corrections if c.action_type == "add")
    removed = sum(1 for c in corrections if c.action_type == "remove")
    adjusted = sum(1 for c in corrections if c.action_type == "adjust")
    split = sum(1 for c in corrections if c.action_type == "split")

    # Calculate corrected count
    original_count = prediction.colony_count
    corrected_count = original_count + added - removed + split

    return CorrectionSummary(
        added=added,
        removed=removed,
        adjusted=adjusted,
        split=split,
        corrected_count=corrected_count,
    )

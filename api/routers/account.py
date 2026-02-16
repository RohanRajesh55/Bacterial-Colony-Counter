"""Router for account settings endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.dependencies import get_current_user
from api.auth.security import hash_password, verify_password
from api.db.models import User
from api.db.session import get_db
from api.schemas.account import PasswordChangeRequest

router = APIRouter(prefix="/account", tags=["account"])


@router.put("/password")
async def change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change the current user's password.

    Args:
        request: Password change request with current and new passwords
        current_user: Authenticated user from JWT cookie
        db: Async database session

    Returns:
        Success message

    Raises:
        HTTPException: 400 if current password is incorrect
    """
    # Verify current password
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Update password
    current_user.hashed_password = hash_password(request.new_password)
    await db.commit()

    return {"message": "Password updated successfully"}

"""FastAPI dependencies for authentication."""

from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from jwt.exceptions import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.security import decode_access_token
from api.db.models import User
from api.db.session import get_db


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Fetch a user by email address.

    Args:
        db: Async database session
        email: Email address to look up

    Returns:
        User object if found, None otherwise
    """
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_optional_user(
    access_token: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Get current user if authenticated, None otherwise.

    Unlike get_current_user, this does not raise 401 for unauthenticated requests.
    Use for endpoints that work for both authenticated and anonymous users.

    Args:
        access_token: JWT token from HttpOnly cookie
        db: Async database session

    Returns:
        User object if authenticated and valid, None otherwise
    """
    if not access_token:
        return None
    try:
        payload = decode_access_token(access_token)
        email = payload.get("sub")
        if not email:
            return None
    except InvalidTokenError:
        return None

    user = await get_user_by_email(db, email)
    if user and user.is_active:
        return user
    return None


async def get_current_user(
    access_token: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency to get current authenticated user from cookie.

    Args:
        access_token: JWT token from HttpOnly cookie
        db: Async database session

    Returns:
        Authenticated User object

    Raises:
        HTTPException: 401 if not authenticated or invalid token
        HTTPException: 403 if account is disabled
    """
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    try:
        payload = decode_access_token(access_token)
        email: str | None = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    user = await get_user_by_email(db, email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account disabled",
        )
    return user

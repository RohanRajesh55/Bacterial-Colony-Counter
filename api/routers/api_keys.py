"""Router for API key management endpoints."""

import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.dependencies import get_current_user
from api.db.models import APIKey, User
from api.db.session import get_db
from api.schemas.api_key import APIKeyCreate, APIKeyCreated, APIKeyResponse

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


def generate_api_key() -> tuple[str, str]:
    """Generate a new API key and its hash.

    Returns:
        Tuple of (full_key, key_hash) where full_key is the displayable key
        and key_hash is the SHA256 hash for storage.
    """
    raw_key = secrets.token_urlsafe(32)
    full_key = f"cfu_{raw_key}"
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    return full_key, key_hash


@router.post("", response_model=APIKeyCreated, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: APIKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new API key for the current user.

    The full API key is returned only once. Store it securely.

    Args:
        request: API key creation request with name
        current_user: Authenticated user from JWT cookie
        db: Async database session

    Returns:
        Created API key with the full key (shown only once)
    """
    full_key, key_hash = generate_api_key()
    prefix = full_key[:12]  # "cfu_" + first 8 chars of random part

    api_key = APIKey(
        user_id=current_user.id,
        key_hash=key_hash,
        name=request.name,
        prefix=prefix,
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)

    # Return with full key (only time it's shown)
    return APIKeyCreated(
        id=api_key.id,
        name=api_key.name,
        prefix=api_key.prefix,
        is_active=api_key.is_active,
        last_used_at=api_key.last_used_at,
        created_at=api_key.created_at,
        key=full_key,
    )


@router.get("", response_model=list[APIKeyResponse])
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all API keys for the current user.

    Note: Full keys are never returned, only the prefix for identification.

    Args:
        current_user: Authenticated user from JWT cookie
        db: Async database session

    Returns:
        List of API keys with prefixes only
    """
    result = await db.execute(
        select(APIKey)
        .where(APIKey.user_id == current_user.id)
        .order_by(APIKey.created_at.desc())
    )
    return result.scalars().all()


@router.delete("/{key_id}")
async def revoke_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke (delete) an API key.

    Args:
        key_id: ID of the API key to revoke
        current_user: Authenticated user from JWT cookie
        db: Async database session

    Returns:
        Success message

    Raises:
        HTTPException: 404 if API key not found or not owned by user
    """
    result = await db.execute(
        select(APIKey).where(
            APIKey.id == key_id, APIKey.user_id == current_user.id
        )
    )
    api_key = result.scalar_one_or_none()

    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    await db.delete(api_key)
    await db.commit()

    return {"message": "API key revoked"}

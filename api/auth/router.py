"""Authentication router with register, login, logout, and password reset endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from api import state
from api.auth.dependencies import get_current_user, get_user_by_email
from api.auth.email import send_reset_email
from api.auth.schemas import (
    ForgotPasswordRequest,
    MessageResponse,
    PasswordResetRequest,
    UserCreate,
    UserResponse,
)
from api.auth.security import (
    create_access_token,
    create_reset_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from api.config import Settings
from api.db.models import User
from api.db.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


def get_settings() -> Settings:
    """Get settings instance (avoids import-time validation)."""
    return Settings()


def set_auth_cookie(response: Response, token: str, settings: Settings) -> None:
    """Set the access_token HttpOnly cookie.

    Args:
        response: FastAPI response object
        token: JWT access token
        settings: Application settings
    """
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=settings.IS_PRODUCTION,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


def clear_auth_cookie(response: Response) -> None:
    """Clear the access_token cookie.

    Args:
        response: FastAPI response object
    """
    response.delete_cookie(key="access_token")


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=MessageResponse)
@state.limiter.limit("3/hour")
async def register(
    request: Request,
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Register a new user account.

    Args:
        request: FastAPI request object (for rate limiting)
        user_data: User registration data (email, password)
        db: Async database session

    Returns:
        Success message

    Raises:
        HTTPException: 400 if email already registered
    """
    existing = await get_user_by_email(db, user_data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    hashed = hash_password(user_data.password)
    user = User(email=user_data.email, hashed_password=hashed)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return MessageResponse(message="User created successfully")


@router.post("/login", response_model=MessageResponse)
@state.limiter.limit("5/minute")
async def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Login with email (as username) and password, sets HttpOnly cookie.

    Uses OAuth2PasswordRequestForm for compatibility with standard OAuth2 flows
    and Swagger UI testing. The username field contains the email address.

    Args:
        response: FastAPI response object for setting cookie
        form_data: OAuth2 form with username (email) and password
        db: Async database session

    Returns:
        Success message with Set-Cookie header

    Raises:
        HTTPException: 401 if invalid credentials
        HTTPException: 403 if account is disabled
    """
    user = await get_user_by_email(db, form_data.username)
    # Always return same error to prevent user enumeration
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account disabled",
        )

    settings = get_settings()
    access_token = create_access_token(data={"sub": user.email})
    set_auth_cookie(response, access_token, settings)

    return MessageResponse(message="Login successful")


@router.post("/logout", response_model=MessageResponse)
async def logout(response: Response) -> MessageResponse:
    """Logout by clearing the auth cookie.

    Args:
        response: FastAPI response object for clearing cookie

    Returns:
        Success message with cookie deletion
    """
    clear_auth_cookie(response)
    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    """Get current authenticated user info.

    Args:
        current_user: Authenticated user from dependency

    Returns:
        User information (id, email, is_active, is_verified, created_at)
    """
    return current_user


@router.post(
    "/forgot-password", status_code=status.HTTP_202_ACCEPTED, response_model=MessageResponse
)
async def forgot_password(
    request: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Request password reset email.

    Always returns 202 to prevent email enumeration - even if the email
    doesn't exist in the system, the response is the same.

    Args:
        request: Contains email address for reset
        db: Async database session

    Returns:
        Generic message indicating email was sent (if account exists)
    """
    user = await get_user_by_email(db, request.email)

    # Only send email if user exists and is active
    # But always return same response to prevent enumeration
    if user and user.is_active:
        token = create_reset_token(user.email)
        await send_reset_email(user.email, token)

    return MessageResponse(message="If the email exists, a reset link has been sent")


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    request: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Reset password using token from email.

    Validates the reset token and updates the user's password.

    Args:
        request: Contains reset token and new password
        db: Async database session

    Returns:
        Success message if password was reset

    Raises:
        HTTPException: 400 if token is invalid, expired, or not a reset token
    """
    try:
        payload = decode_access_token(request.token)
        # Verify this is a reset token, not an access token
        if payload.get("type") != "reset":
            raise HTTPException(status_code=400, detail="Invalid or expired token")
        email = payload.get("sub")
    except InvalidTokenError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user = await get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user.hashed_password = hash_password(request.new_password)
    await db.commit()

    return MessageResponse(message="Password reset successful")

"""Health check endpoint."""

from fastapi import APIRouter

from api.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check API health status."""
    return HealthResponse(status="healthy")

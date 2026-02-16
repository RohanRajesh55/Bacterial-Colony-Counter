"""FastAPI application entry point for CFU-Counter API."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_pagination import add_pagination
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from api.auth.router import router as auth_router
from api.config import Settings
from api.middleware import SecurityHeadersMiddleware
from api.routers import account, api_keys, corrections, feedback, health, history, predict
from api.services.rtdetr_service import RTDetrService
from api import state
from api.state import ml_models
from api.storage import ensure_bucket_exists

# Load settings
settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - load models at startup, cleanup at shutdown."""
    # Startup: Load model
    print("Loading RT-DETR model...")
    ml_models["rtdetr"] = RTDetrService()
    print(f"Model loaded on device: {ml_models['rtdetr'].device}")

    # Ensure storage bucket exists (skip if MinIO unavailable)
    try:
        ensure_bucket_exists(settings.S3_BUCKET_NAME)
        print(f"MinIO bucket ensured: {settings.S3_BUCKET_NAME}")
    except Exception as e:
        print(f"WARNING: MinIO unavailable ({e}). Storage features disabled.")
    yield
    # Shutdown: Cleanup
    print("Shutting down, clearing models...")
    ml_models.clear()


# Create FastAPI app
app = FastAPI(
    title="CFU-Counter API",
    description="API for bacterial colony counting from petri dish images",
    version="0.1.0",
    lifespan=lifespan,
    debug=not settings.IS_PRODUCTION,
)

# Add Security Headers Middleware
app.add_middleware(SecurityHeadersMiddleware)

# Add Rate Limiting Middleware
app.state.limiter = state.limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
# Health endpoint without prefix: GET /health
app.include_router(health.router)
# Auth endpoints with /api prefix: /api/auth/*
app.include_router(auth_router, prefix="/api")
# Predict endpoint with /api prefix: POST /api/predict
app.include_router(predict.router, prefix="/api")
# Feedback endpoint with /api prefix: POST /api/feedback
app.include_router(feedback.router, prefix="/api")
# History endpoint with /api prefix: GET /api/history
app.include_router(history.router, prefix="/api")
# Account endpoint with /api prefix: PUT /api/account/password
app.include_router(account.router, prefix="/api")
# API keys endpoints with /api prefix: /api/api-keys/*
app.include_router(api_keys.router, prefix="/api")
# Corrections endpoints with /api prefix: /api/corrections/*
app.include_router(corrections.router, prefix="/api")

# Add pagination support
add_pagination(app)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)

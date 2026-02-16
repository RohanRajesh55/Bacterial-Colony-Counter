"""Configuration settings for the CFU-Counter API."""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:3000"],
        description="Allowed origins for CORS",
    )
    MAX_FILE_SIZE: int = Field(
        default=20 * 1024 * 1024,  # 20MB
        description="Maximum allowed file size in bytes",
    )
    ALLOWED_CONTENT_TYPES: set[str] = Field(
        default={"image/jpeg", "image/png"},
        description="Allowed image content types",
    )
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/cfu_counter",
        description="PostgreSQL connection URL for async database operations",
    )

    # S3/MinIO Object Storage Settings
    S3_ENDPOINT_URL: str = Field(
        default="http://localhost:9000",
        description="S3-compatible endpoint URL (MinIO)",
    )
    S3_ACCESS_KEY: str = Field(
        default="minioadmin",
        description="S3 access key ID",
    )
    S3_SECRET_KEY: str = Field(
        default="minioadmin",
        description="S3 secret access key",
    )
    S3_BUCKET_NAME: str = Field(
        default="cfu-images",
        description="S3 bucket name for storing images",
    )
    S3_REGION: str = Field(
        default="us-east-1",
        description="S3 region (required for signature)",
    )

    # JWT Authentication Settings
    JWT_SECRET_KEY: str = Field(
        description="Secret key for JWT signing (generate with: openssl rand -hex 32)",
    )
    JWT_ALGORITHM: str = Field(
        default="HS256",
        description="Algorithm for JWT encoding",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        description="Access token expiration time in minutes",
    )

    # Email Settings (for password reset)
    MAIL_USERNAME: str = Field(
        default="",
        description="SMTP username for sending emails",
    )
    MAIL_PASSWORD: str = Field(
        default="",
        description="SMTP password for sending emails",
    )
    MAIL_FROM: str = Field(
        default="noreply@cfu-counter.com",
        description="From address for outgoing emails",
    )
    MAIL_SERVER: str = Field(
        default="smtp.gmail.com",
        description="SMTP server hostname",
    )
    MAIL_PORT: int = Field(
        default=587,
        description="SMTP server port",
    )

    # Application Settings
    FRONTEND_URL: str = Field(
        default="http://localhost:3000",
        description="Frontend URL for password reset links",
    )
    IS_PRODUCTION: bool = Field(
        default=False,
        description="Controls cookie secure flag and other production settings",
    )

    model_config = {
        "env_file": ".env",
        "env_prefix": "CFU_",
        "case_sensitive": False,
        "extra": "ignore",  # Allow extra env vars (e.g., for RunPod scripts)
    }

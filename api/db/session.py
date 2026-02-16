"""Async database session management."""

from collections.abc import AsyncGenerator
from functools import cache

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.config import Settings


@cache
def get_settings() -> Settings:
    """Get settings instance (cached, avoids import-time validation)."""
    return Settings()


@cache
def get_engine():
    """Get database engine (cached, created on first access)."""
    settings = get_settings()
    return create_async_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        echo=False,
    )


@cache
def get_session_maker():
    """Get session maker (cached, created on first access)."""
    return async_sessionmaker(
        get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session.

    This is a dependency for FastAPI routes that need database access.
    The session is automatically closed when the request completes.
    """
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
        finally:
            await session.close()

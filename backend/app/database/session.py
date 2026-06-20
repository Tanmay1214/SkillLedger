"""Async database engine and session factory."""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# Configure connection pool parameters. Postgres supports/needs pool size constraints,
# while SQLite (used in tests) uses StaticPool/NullPool and raises TypeError on pool_size.
pool_kwargs = {}
if "postgresql" in settings.database_url:
    pool_kwargs["pool_size"] = 10
    pool_kwargs["max_overflow"] = 20
    pool_kwargs["pool_pre_ping"] = True

engine = create_async_engine(
    settings.database_url,
    echo=settings.environment == "development" and settings.log_level == "DEBUG",
    **pool_kwargs,
)

# `expire_on_commit=False` so returned ORM objects stay usable after commit.
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async session.

    Automatically rolls back on exception and always closes the session.
    """
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


__all__ = ["engine", "async_session_factory", "get_db"]

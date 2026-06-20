"""Pytest configuration + shared fixtures.

We isolate tests from real environment values by setting required env vars
before importing the app. A test in-memory SQLite DB is used for the unit
tests that need a session; HTTP-level flow tests stub the GitHub client.
"""
from __future__ import annotations

import os

# Provide deterministic test env BEFORE any app import.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("GITHUB_CLIENT_ID", "test_client_id")
os.environ.setdefault("GITHUB_CLIENT_SECRET", "test_client_secret")
os.environ.setdefault("JWT_SECRET", "test_jwt_secret_at_least_32_chars_long_xx")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")
os.environ.setdefault("BACKEND_URL", "http://localhost:8000")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")

import asyncio
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database.base import Base
from app.database.session import get_db
from app.main import create_app

# Reset the cached settings so test env vars take effect.
from app.core.config import get_settings
get_settings.cache_clear()


@pytest_asyncio.fixture
async def engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    
    # Import all models to register them with Base.metadata before calling create_all
    import app.models
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()



@pytest_asyncio.fixture
async def db_session(engine) -> AsyncIterator:
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture
async def app(engine):
    application = create_app()

    factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async def override_get_db():
        async with factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    application.dependency_overrides[get_db] = override_get_db
    yield application
    application.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

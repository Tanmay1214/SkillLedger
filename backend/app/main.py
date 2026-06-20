"""FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.exception_handlers import register_exception_handlers
from app.api.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.middleware.session_middleware import SessionValidationMiddleware


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Startup
    configure_logging()
    yield
    # Shutdown: dispose DB engine (clean connection pool).
    from app.database.session import engine

    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="SkillLedger API",
        description="GitHub OAuth authentication module for SkillLedger.",
        version="0.1.0",
        docs_url="/api/v1/docs",
        openapi_url="/api/v1/openapi.json",
        lifespan=lifespan,
    )

    # ---- CORS ----
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins or [str(settings.frontend_url)],
        allow_credentials=True,  # required so cookies cross the port boundary
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---- Session validation (sliding refresh + request.state.user_id) ----
    app.add_middleware(SessionValidationMiddleware)

    # ---- Routers + handlers ----
    app.include_router(api_router)
    register_exception_handlers(app)

    # ---- Liveness ----
    @app.get("/health", tags=["meta"], summary="Liveness probe")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()


__all__ = ["app", "create_app"]

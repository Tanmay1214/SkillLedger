"""Centralized exception handlers.

Map domain exceptions to consistent JSON error bodies so the frontend can
branch on `error_code`.
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.auth.exceptions import AuthError
from app.schemas.errors import ErrorResponse
from app.services.github_service import GitHubOAuthError


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AuthError)
    async def _auth_error(_: Request, exc: AuthError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(detail=str(exc), error_code=exc.error_code).model_dump(),
        )

    @app.exception_handler(GitHubOAuthError)
    async def _github_error(_: Request, exc: GitHubOAuthError) -> JSONResponse:
        return JSONResponse(
            status_code=502,
            content=ErrorResponse(detail=str(exc), error_code="github_error").model_dump(),
        )


__all__ = ["register_exception_handlers"]

"""Authentication flow schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl


class AuthUrlResponse(BaseModel):
    """Response of `GET /auth/github/login` — the URL to redirect the browser to."""

    authorization_url: HttpUrl = Field(
        ..., description="GitHub OAuth authorize URL (with state + scopes)"
    )
    state: str = Field(..., description="Opaque CSRF state echoed in the cookie")


class CallbackSuccess(BaseModel):
    """Response of `GET /auth/github/callback` after a successful login."""

    user: dict = Field(..., description="Public user object (same shape as /auth/me)")
    redirect_to: HttpUrl = Field(..., description="Where the frontend should navigate")


class TokenPair(BaseModel):
    """A pair of JWTs — used internally and by the refresh endpoint."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LogoutResponse(BaseModel):
    """Response of `POST /auth/logout`."""

    message: str = "Logged out"


__all__ = ["AuthUrlResponse", "CallbackSuccess", "TokenPair", "LogoutResponse"]

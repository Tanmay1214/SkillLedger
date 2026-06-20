"""Shared API dependencies and constants."""
from __future__ import annotations

from fastapi import Response

from app.core.config import settings

# Cookie name for the opaque OAuth state token (CSRF defense).
OAUTH_STATE_COOKIE = "skillledger_oauth_state"


def set_state_cookie(response: Response, signed_state: str) -> None:
    """Set the short-lived OAuth state cookie (mirrors the `state` param)."""
    response.set_cookie(
        key=OAUTH_STATE_COOKIE,
        value=signed_state,
        max_age=600,  # 10 minutes, matches oauth_service.STATE_TTL_SECONDS
        httponly=True,
        secure=settings.cookie_https_only,
        samesite="lax",
        path="/",
    )


def clear_state_cookie(response: Response) -> None:
    response.delete_cookie(key=OAUTH_STATE_COOKIE, path="/")


__all__ = ["OAUTH_STATE_COOKIE", "clear_state_cookie", "set_state_cookie"]

"""Cookie helpers.

The access + refresh JWTs live in httpOnly cookies so they are inaccessible
to JavaScript (XSS-resistant). `Secure` is enabled in production; `SameSite`
is `lax` which still allows the top-level OAuth callback redirect to send
the cookie while blocking cross-site POST CSRF.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import Response

from app.core.config import settings


def set_auth_cookies(
    response: Response,
    *,
    access_token: str,
    refresh_token: str,
    access_expires_at: datetime,
    refresh_expires_at: datetime,
) -> None:
    """Set both auth cookies with hardened attributes."""
    common = {
        "httponly": True,
        "secure": settings.cookie_https_only,
        "samesite": settings.cookie_samesite,
        "path": "/",
    }
    response.set_cookie(
        key=settings.session_cookie_name,
        value=access_token,
        expires=access_expires_at,
        **common,
    )
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=refresh_token,
        expires=refresh_expires_at,
        **common,
    )


def clear_auth_cookies(response: Response) -> None:
    """Delete both auth cookies."""
    for name in (settings.session_cookie_name, settings.refresh_cookie_name):
        response.delete_cookie(
            key=name,
            path="/",
            domain=None,
            secure=settings.cookie_https_only,
            httponly=True,
            samesite=settings.cookie_samesite,
        )


def read_access_token_from_cookies(request_cookies) -> str | None:  # type: ignore[no-untyped-def]
    return request_cookies.get(settings.session_cookie_name)


def read_refresh_token_from_cookies(request_cookies) -> str | None:  # type: ignore[no-untyped-def]
    return request_cookies.get(settings.refresh_cookie_name)


__all__ = [
    "set_auth_cookies",
    "clear_auth_cookies",
    "read_access_token_from_cookies",
    "read_refresh_token_from_cookies",
]

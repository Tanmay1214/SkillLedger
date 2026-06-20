"""Domain-specific auth exceptions mapped to HTTP responses by handlers."""
from __future__ import annotations


class AuthError(Exception):
    """Base auth error. Subclasses set a default HTTP status."""

    status_code: int = 401
    error_code: str = "auth_error"

    def __init__(self, message: str = "Authentication error", *, status_code: int | None = None) -> None:
        super().__init__(message)
        if status_code is not None:
            self.status_code = status_code


class InvalidSessionError(AuthError):
    """No valid access token present."""

    error_code = "invalid_session"


class InvalidStateError(AuthError):
    """OAuth state cookie missing or did not match."""

    status_code = 400
    error_code = "invalid_state"


class OAuthCallbackError(AuthError):
    """GitHub returned an error or we failed to complete the handshake."""

    status_code = 502
    error_code = "oauth_callback_failed"


__all__ = [
    "AuthError",
    "InvalidSessionError",
    "InvalidStateError",
    "OAuthCallbackError",
]

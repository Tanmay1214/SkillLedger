"""JWT access + refresh token creation and verification.

Access token:  short-lived (minutes), carries `sub` (user id) + `type=access`.
Refresh token: long-lived (days), carries `sub` + `jti` (unique id, persisted
               in `refresh_sessions` so we can revoke it) + `type=refresh`.

Signed with HS256 using `JWT_SECRET`. Tokens are never placed in localStorage
by the frontend — they ride in httpOnly cookies set by this backend.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from jwt import InvalidTokenError

from app.core.config import settings

TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"


@dataclass(frozen=True, slots=True)
class TokenData:
    """Decoded claims we care about."""

    sub: int
    type: str
    jti: str | None
    exp: datetime


@dataclass(frozen=True, slots=True)
class IssuedTokens:
    """A freshly issued access + refresh token pair."""

    access_token: str
    refresh_token: str
    access_expires_at: datetime
    refresh_expires_at: datetime


def _now() -> datetime:
    return datetime.now(tz=timezone.utc).replace(microsecond=0)


def _encode(payload: dict[str, object]) -> str:
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: int) -> tuple[str, datetime]:
    exp_delta = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    exp = _now() + exp_delta
    payload = {
        "sub": str(user_id),
        "type": TOKEN_TYPE_ACCESS,
        "iat": _now(),
        "exp": exp,
    }
    return _encode(payload), exp


def create_refresh_token(user_id: int) -> tuple[str, datetime, str]:
    """Return (token, expires_at, jti). The caller persists `jti`."""
    exp_delta = timedelta(days=settings.jwt_refresh_token_expire_days)
    exp = _now() + exp_delta
    jti = uuid.uuid4().hex
    payload = {
        "sub": str(user_id),
        "type": TOKEN_TYPE_REFRESH,
        "jti": jti,
        "iat": _now(),
        "exp": exp,
    }
    return _encode(payload), exp, jti


def issue_token_pair(user_id: int) -> IssuedTokens:
    access_token, access_exp = create_access_token(user_id)
    refresh_token, refresh_exp, _ = create_refresh_token(user_id)
    return IssuedTokens(
        access_token=access_token,
        refresh_token=refresh_token,
        access_expires_at=access_exp,
        refresh_expires_at=refresh_exp,
    )


def decode_token(token: str, expected_type: str | None = None) -> TokenData:
    """Decode + validate a JWT. Raises `InvalidTokenError` on any failure."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except InvalidTokenError:
        raise
    if expected_type and payload.get("type") != expected_type:
        raise InvalidTokenError(f"Unexpected token type: {payload.get('type')!r}")
    sub = payload.get("sub")
    if sub is None:
        raise InvalidTokenError("Missing subject claim")
    exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    return TokenData(sub=int(sub), type=payload["type"], jti=payload.get("jti"), exp=exp)


__all__ = [
    "TOKEN_TYPE_ACCESS",
    "TOKEN_TYPE_REFRESH",
    "IssuedTokens",
    "TokenData",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "issue_token_pair",
]

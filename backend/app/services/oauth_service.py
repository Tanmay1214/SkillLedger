"""GitHub OAuth helpers: authorization URL generation + state/CSRF.

The OAuth state parameter is a random, one-time token. We embed a
cryptographically signed version in a short-lived cookie so that, on the
callback, we can verify the request actually originated from us (CSRF
defense) and matches this flow (replay defense).
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass
from urllib.parse import urlencode

from app.core.config import settings

# Scopes: read user profile + email (private emails are not in the default
# `/user` payload, so we need `user:email`).
GITHUB_SCOPES = ["read:user", "user:email"]

# State cookie / signed-token lifetime (seconds). Short — only spans the
# user's round trip to GitHub.
STATE_TTL_SECONDS = 600


@dataclass(frozen=True, slots=True)
class AuthorizationRequest:
    """Result of building an OAuth authorization URL."""

    authorization_url: str
    state: str


def _sign_state(raw_state: str) -> str:
    """Return an HMAC-SHA256 hex signature of `raw_state` using JWT secret."""
    key = settings.jwt_secret.encode("utf-8")
    return hmac.new(key, raw_state.encode("utf-8"), hashlib.sha256).hexdigest()


def generate_state() -> str:
    """Generate a random, URL-safe opaque state token."""
    return secrets.token_urlsafe(32)


def build_signed_state(raw_state: str) -> str:
    """Return `raw_state.signature.timestamp` so we can verify later.

    Format:  <state>.<signature>.<issued_unix_ts>
    """
    ts = int(time.time())
    sig = _sign_state(f"{raw_state}:{ts}")
    return f"{raw_state}.{sig}.{ts}"


def verify_signed_state(signed: str, expected_raw: str) -> bool:
    """Validate a signed state token returned from GitHub.

    Checks:
      * structural integrity (3 dot-separated parts),
      * HMAC signature match,
      * not expired (within STATE_TTL_SECONDS).
    Constant-time comparison is used for the signature.
    """
    parts = signed.split(".")
    if len(parts) != 3:
        return False
    raw_state, sig, ts_str = parts
    if not hmac.compare_digest(raw_state, expected_raw):
        return False
    try:
        ts = int(ts_str)
    except ValueError:
        return False
    if time.time() - ts > STATE_TTL_SECONDS:
        return False
    expected_sig = _sign_state(f"{raw_state}:{ts}")
    return hmac.compare_digest(sig, expected_sig)


def build_authorization_url(raw_state: str) -> AuthorizationRequest:
    """Build the GitHub OAuth authorize URL for the Authorization Code Flow."""
    signed = build_signed_state(raw_state)
    params = {
        "client_id": settings.github_client_id,
        "redirect_uri": f"{str(settings.backend_url).rstrip('/')}/api/v1/auth/github/callback/redirect",
        "scope": " ".join(GITHUB_SCOPES),
        "state": signed,
        "allow_signup": "true",
    }
    url = f"{settings.github_authorize_url}?{urlencode(params)}"
    return AuthorizationRequest(authorization_url=url, state=signed)

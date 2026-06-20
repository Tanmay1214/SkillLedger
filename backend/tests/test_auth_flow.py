"""End-to-end OAuth flow test via the FastAPI test client.

Mocks the GitHub OAuth service at the boundary (token exchange + profile
fetch) so we test *our* flow: state cookie, callback, JWT issuance, cookie
setting, /auth/me, and /auth/logout.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.api.deps import OAUTH_STATE_COOKIE
from app.services import jwt_service


GITHUB_PROFILE_PAYLOAD = {
    "id": 99,
    "login": "flowuser",
    "name": "Flow User",
    "email": "flow@example.com",
    "avatar_url": "https://avatars.githubusercontent.com/u/99",
    "html_url": "https://github.com/flowuser",
}


async def test_full_oauth_flow_login_callback_me_logout(client):
    # 1. Login -> get authorize URL + state cookie
    login_resp = await client.get("/api/v1/auth/github/login")
    assert login_resp.status_code == 200
    body = login_resp.json()
    assert "github.com/login/oauth/authorize" in body["authorization_url"]
    state = body["state"]

    # carry the state cookie through subsequent requests
    cookies = client.cookies

    # 2. Mock GitHub at the boundary and hit the callback
    with patch(
        "app.api.auth_routes.github_service.exchange_code_for_token",
        new=AsyncMock(return_value="gho_fake_token"),
    ), patch(
        "app.api.auth_routes.github_service.fetch_profile",
        new=AsyncMock(return_value=__import__("app.schemas.user", fromlist=["GithubProfile"]).GithubProfile(
            **GITHUB_PROFILE_PAYLOAD
        )),
    ):
        callback_resp = await client.get(
            "/api/v1/auth/github/callback",
            params={"code": "fake_code", "state": state},
            cookies={OAUTH_STATE_COOKIE: state},
        )
    assert callback_resp.status_code == 200, callback_resp.text
    cb = callback_resp.json()
    assert cb["user"]["username"] == "flowuser"
    assert "/dashboard" in cb["redirect_to"]

    # The callback should have set the session cookies.
    # httpx TestClient tracks them via the `Set-Cookie` headers.
    assert any("skillledger_session" in c for c in client.cookies.keys())

    # 3. /auth/me with the session cookie should return the user
    me_resp = await client.get("/api/v1/auth/me")
    assert me_resp.status_code == 200
    me = me_resp.json()
    assert me["username"] == "flowuser"
    assert me["github_id"] == 99
    assert me["email"] == "flow@example.com"

    # 4. Logout clears the session
    logout_resp = await client.post("/api/v1/auth/logout")
    assert logout_resp.status_code == 200

    # 5. After logout, /auth/me should 401 (cookie cleared)
    me_after = await client.get("/api/v1/auth/me")
    assert me_after.status_code == 401


async def test_callback_rejects_missing_state(client):
    resp = await client.get(
        "/api/v1/auth/github/callback",
        params={"code": "x", "state": "x"},
    )
    assert resp.status_code == 400  # InvalidStateError


async def test_callback_rejects_state_mismatch(client):
    login_resp = await client.get("/api/v1/auth/github/login")
    valid_state = login_resp.json()["state"]
    # Send a different (tampered) state than the cookie holds
    resp = await client.get(
        "/api/v1/auth/github/callback",
        params={"code": "x", "state": "totally.different.123"},
        cookies={OAUTH_STATE_COOKIE: valid_state},
    )
    assert resp.status_code == 400


async def test_callback_handles_github_denial(client):
    login_resp = await client.get("/api/v1/auth/github/login")
    state = login_resp.json()["state"]
    resp = await client.get(
        "/api/v1/auth/github/callback",
        params={"error": "access_denied"},
        cookies={OAUTH_STATE_COOKIE: state},
    )
    assert resp.status_code == 502  # OAuthCallbackError


async def test_me_unauthenticated(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


async def test_refresh_endpoint_rotates(client):
    # Issue tokens directly (bypass OAuth) by hitting login + callback flow,
    # then call /auth/refresh.
    from unittest.mock import AsyncMock as _AM, patch as _P

    login_resp = await client.get("/api/v1/auth/github/login")
    state = login_resp.json()["state"]
    with _P(
        "app.api.auth_routes.github_service.exchange_code_for_token",
        new=_AM(return_value="gho_fake"),
    ), _P(
        "app.api.auth_routes.github_service.fetch_profile",
        new=_AM(return_value=__import__("app.schemas.user", fromlist=["GithubProfile"]).GithubProfile(
            **GITHUB_PROFILE_PAYLOAD
        )),
    ):
        await client.get(
            "/api/v1/auth/github/callback",
            params={"code": "c", "state": state},
            cookies={OAUTH_STATE_COOKIE: state},
        )
    resp = await client.post("/api/v1/auth/refresh")
    assert resp.status_code == 200


async def test_callback_redirect_endpoint(client):
    login_resp = await client.get("/api/v1/auth/github/login")
    state = login_resp.json()["state"]

    with patch(
        "app.api.auth_routes.github_service.exchange_code_for_token",
        new=AsyncMock(return_value="gho_fake_token"),
    ), patch(
        "app.api.auth_routes.github_service.fetch_profile",
        new=AsyncMock(return_value=__import__("app.schemas.user", fromlist=["GithubProfile"]).GithubProfile(
            **GITHUB_PROFILE_PAYLOAD
        )),
    ):
        resp = await client.get(
            "/api/v1/auth/github/callback/redirect",
            params={"code": "fake_code", "state": state},
            cookies={OAUTH_STATE_COOKIE: state},
            follow_redirects=False,
        )
    assert resp.status_code == 302
    assert "dashboard" in resp.headers["location"]
    assert any("skillledger_session" in c for c in client.cookies.keys())

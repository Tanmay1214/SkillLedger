"""Unit tests for the GitHub OAuth client (token exchange + profile fetch).

GitHub's HTTP calls are mocked with respx so no network is required.
"""
from __future__ import annotations

import httpx
import pytest
import respx

from app.services import github_service


@respx.mock
async def test_exchange_code_for_token_success():
    respx.post("https://github.com/login/oauth/access_token").mock(
        return_value=httpx.Response(200, json={"access_token": "gho_abc", "token_type": "bearer"})
    )
    token = await github_service.exchange_code_for_token("code123")
    assert token == "gho_abc"


@respx.mock
async def test_exchange_code_for_token_error():
    respx.post("https://github.com/login/oauth/access_token").mock(
        return_value=httpx.Response(200, json={"error": "bad_verification_code"})
    )
    with pytest.raises(github_service.GitHubOAuthError):
        await github_service.exchange_code_for_token("bad")


@respx.mock
async def test_fetch_profile_with_public_email():
    respx.get("https://api.github.com/user").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": 1,
                "login": "octocat",
                "name": "Octo",
                "email": "octo@example.com",
                "avatar_url": "https://avatars.githubusercontent.com/u/1",
                "html_url": "https://github.com/octocat",
            },
        )
    )
    profile = await github_service.fetch_profile("tok")
    assert profile.id == 1
    assert profile.email == "octo@example.com"


@respx.mock
async def test_fetch_profile_resolves_private_email():
    # /user omits email (private) -> client should call /user/emails
    respx.get("https://api.github.com/user").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": 2,
                "login": "secret",
                "name": "Secret",
                "email": None,
                "avatar_url": "https://avatars.githubusercontent.com/u/2",
                "html_url": "https://github.com/secret",
            },
        )
    )
    respx.get("https://api.github.com/user/emails").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"email": "unverified@x.com", "primary": False, "verified": False},
                {"email": "real@x.com", "primary": True, "verified": True},
            ],
        )
    )
    profile = await github_service.fetch_profile("tok")
    assert profile.email == "real@x.com"

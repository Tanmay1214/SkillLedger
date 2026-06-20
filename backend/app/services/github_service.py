"""GitHub API client — token exchange + profile retrieval.

All network calls use `httpx.AsyncClient`. Errors are translated into a
domain `GitHubOAuthError` so the API layer can map them to HTTP 502/400
without leaking GitHub internals.
"""
from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings
from app.schemas.user import GithubProfile


class GitHubOAuthError(Exception):
    """Raised when GitHub rejects an OAuth step or returns invalid data."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


GITHUB_MEDIA_TYPE = "application/vnd.github+json"
DEFAULT_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


def _auth_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": GITHUB_MEDIA_TYPE,
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "SkillLedger/0.1",
    }


async def exchange_code_for_token(code: str, redirect_uri: str | None = None) -> str:
    """Exchange an authorization code for a GitHub access token.

    Uses the Authorization Code Flow: the client secret is sent only to
    GitHub's token endpoint, never to the browser.
    """
    if redirect_uri is None:
        redirect_uri = f"{str(settings.backend_url).rstrip('/')}/api/v1/auth/github/callback"
    data = {
        "client_id": settings.github_client_id,
        "client_secret": settings.github_client_secret,
        "code": code,
        # The redirect_uri MUST match the one used in the authorize request.
        "redirect_uri": redirect_uri,
    }
    headers = {"Accept": GITHUB_MEDIA_TYPE, "User-Agent": "SkillLedger/0.1"}

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        resp = await client.post(settings.github_token_url, data=data, headers=headers)

    if resp.status_code != 200:
        raise GitHubOAuthError(
            f"GitHub token exchange failed (HTTP {resp.status_code})",
            status_code=resp.status_code,
        )

    # GitHub returns JSON when Accept is set, but historically returned form
    # data. Guard against both.
    payload: dict[str, Any]
    try:
        payload = resp.json()
    except ValueError:
        payload = dict(httpx.QueryParams(resp.text))

    if payload.get("error"):
        raise GitHubOAuthError(
            f"GitHub OAuth error: {payload.get('error_description') or payload['error']}"
        )

    token = payload.get("access_token")
    if not token:
        raise GitHubOAuthError("GitHub token response missing access_token")
    return token


async def fetch_profile(access_token: str) -> GithubProfile:
    """Fetch the authenticated user's profile from `/user`.

    Falls back to `/user/emails` when the primary email is private (GitHub
    omits `email` from `/user` for private-email accounts).
    """
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        profile_resp = await client.get(
            f"{settings.github_api_url}/user",
            headers=_auth_headers(access_token),
        )
        if profile_resp.status_code != 200:
            raise GitHubOAuthError(
                f"GitHub profile fetch failed (HTTP {profile_resp.status_code})",
                status_code=profile_resp.status_code,
            )
        profile_data = profile_resp.json()

        # Resolve a private/missing email.
        if not profile_data.get("email"):
            email = await _fetch_primary_email(client, access_token)
            if email:
                profile_data["email"] = email

    return GithubProfile.model_validate(profile_data)


async def _fetch_primary_email(client: httpx.AsyncClient, access_token: str) -> str | None:
    """Return the user's primary, verified email from `/user/emails`."""
    resp = await client.get(
        f"{settings.github_api_url}/user/emails",
        headers=_auth_headers(access_token),
    )
    if resp.status_code != 200:
        return None
    emails = resp.json()
    if not isinstance(emails, list):
        return None
    # Prefer primary + verified; otherwise the first verified; otherwise first.
    for e in emails:
        if e.get("primary") and e.get("verified"):
            return e.get("email")
    for e in emails:
        if e.get("verified"):
            return e.get("email")
    return emails[0].get("email") if emails else None


async def fetch_user_repositories(access_token: str) -> list[dict[str, Any]]:
    """Fetch the authenticated user's repositories from `/user/repos`."""
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        # Fetch repos where the user is an owner or collaborator
        resp = await client.get(
            f"{settings.github_api_url}/user/repos?per_page=100",
            headers=_auth_headers(access_token),
        )
        if resp.status_code != 200:
            raise GitHubOAuthError(
                f"GitHub repositories fetch failed (HTTP {resp.status_code})",
                status_code=resp.status_code,
            )
        return resp.json()


async def fetch_repository_by_id(access_token: str, github_repo_id: int) -> dict[str, Any]:
    """Fetch repository metadata by GitHub repository ID."""
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        resp = await client.get(
            f"{settings.github_api_url}/repositories/{github_repo_id}",
            headers=_auth_headers(access_token),
        )
        if resp.status_code != 200:
            # Fall back: list user's repositories and search by ID
            repos = await fetch_user_repositories(access_token)
            for r in repos:
                if r.get("id") == github_repo_id:
                    return r
            raise GitHubOAuthError(
                f"GitHub repository with ID {github_repo_id} not found (HTTP {resp.status_code})",
                status_code=resp.status_code,
            )
        return resp.json()


async def fetch_repository_languages(access_token: str, owner: str, repo: str) -> dict[str, int]:
    """Fetch repository languages breakdown from `/repos/{owner}/{repo}/languages`."""
    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        resp = await client.get(
            f"{settings.github_api_url}/repos/{owner}/{repo}/languages",
            headers=_auth_headers(access_token),
        )
        if resp.status_code != 200:
            return {}
        return resp.json()


__all__ = [
    "GitHubOAuthError",
    "exchange_code_for_token",
    "fetch_profile",
    "fetch_user_repositories",
    "fetch_repository_by_id",
    "fetch_repository_languages",
]


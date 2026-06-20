"""Unit tests for user upsert + refresh session lifecycle."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.schemas.user import GithubProfile
from app.services import auth_service, user_service


@pytest.fixture
def github_profile():
    return GithubProfile(
        id=12345,
        login="octocat",
        name="The Octocat",
        email="octocat@example.com",
        avatar_url="https://avatars.githubusercontent.com/u/583231?v=4",
        html_url="https://github.com/octocat",
    )


async def test_upsert_creates_new_user(db_session, github_profile):
    user = await user_service.upsert_user_from_github(db_session, github_profile, "gh_tok")
    await db_session.commit()

    assert user.id is not None
    assert user.github_id == 12345
    assert user.username == "octocat"
    assert user.email == "octocat@example.com"
    assert user.access_token == "gh_tok"


async def test_upsert_updates_existing_user(db_session, github_profile):
    # First login
    await user_service.upsert_user_from_github(db_session, github_profile, "gh_tok_1")
    await db_session.commit()

    # Second login with new token + changed name
    updated = github_profile.model_copy(update={"name": "Octo Renamed"})
    user = await user_service.upsert_user_from_github(db_session, updated, "gh_tok_2")
    await db_session.commit()

    assert user.name == "Octo Renamed"
    assert user.access_token == "gh_tok_2"
    # Same row, not a duplicate
    again = await user_service.get_user_by_github_id(db_session, 12345)
    assert again.id == user.id


async def test_get_user_by_id_returns_none_when_missing(db_session):
    assert await user_service.get_user_by_id(db_session, 9999) is None


async def test_refresh_session_create_is_valid_revoke(db_session, github_profile):
    user = await user_service.upsert_user_from_github(db_session, github_profile, "tok")
    await db_session.commit()

    jti = "abc-jti"
    exp = datetime.now(tz=timezone.utc) + timedelta(days=1)
    await auth_service.create(db_session, user_id=user.id, jti=jti, expires_at=exp)
    await db_session.commit()

    assert await auth_service.is_valid(db_session, jti) is True

    await auth_service.revoke(db_session, jti)
    await db_session.commit()
    assert await auth_service.is_valid(db_session, jti) is False


async def test_refresh_session_revoke_all(db_session, github_profile):
    user = await user_service.upsert_user_from_github(db_session, github_profile, "tok")
    await db_session.commit()

    exp = datetime.now(tz=timezone.utc) + timedelta(days=1)
    for jti in ("a", "b", "c"):
        await auth_service.create(db_session, user_id=user.id, jti=jti, expires_at=exp)
    await db_session.commit()

    count = await auth_service.revoke_all_for_user(db_session, user.id)
    await db_session.commit()
    assert count == 3
    for jti in ("a", "b", "c"):
        assert await auth_service.is_valid(db_session, jti) is False


async def test_expired_session_is_invalid(db_session, github_profile):
    user = await user_service.upsert_user_from_github(db_session, github_profile, "tok")
    await db_session.commit()

    exp = datetime.now(tz=timezone.utc) - timedelta(days=1)  # past
    await auth_service.create(db_session, user_id=user.id, jti="expired", expires_at=exp)
    await db_session.commit()
    assert await auth_service.is_valid(db_session, "expired") is False

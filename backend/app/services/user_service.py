"""User creation / lookup service (upsert by GitHub identity)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import GithubProfile


async def get_user_by_github_id(db: AsyncSession, github_id: int) -> User | None:
    stmt = select(User).where(User.github_id == github_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    stmt = select(User).where(User.username == username)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def upsert_user_from_github(
    db: AsyncSession,
    profile: GithubProfile,
    github_access_token: str,
) -> User:
    """Create the user if new, otherwise update mutable fields.

    Identity is keyed on `github_id` (immutable on GitHub's side). The GitHub
    `access_token` is refreshed on every login so it stays current.
    """
    user = await get_user_by_github_id(db, profile.id)

    fields = {
        "username": profile.login,
        "name": profile.name,
        "email": profile.email,
        "avatar_url": str(profile.avatar_url) if profile.avatar_url else None,
        "profile_url": str(profile.html_url) if profile.html_url else None,
        "access_token": github_access_token,
    }

    if user is None:
        # Handle a rare race: username collision with a different github_id.
        existing = await get_user_by_username(db, profile.login)
        if existing is not None and existing.github_id != profile.id:
            # Disambiguate to avoid violating the username unique constraint.
            fields["username"] = f"{profile.login}-gh{profile.id}"

        user = User(github_id=profile.id, **fields)
        db.add(user)
    else:
        for key, value in fields.items():
            setattr(user, key, value)

    await db.flush()
    await db.refresh(user)
    return user


__all__ = [
    "get_user_by_github_id",
    "get_user_by_id",
    "get_user_by_username",
    "upsert_user_from_github",
]

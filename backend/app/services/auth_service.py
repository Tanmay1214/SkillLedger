"""Refresh-session service.

Wraps the lifecycle of a refresh token:
  * `create`    — persist a new (user, jti) row when issuing a token pair.
  * `is_valid`  — confirm a refresh token's jti is non-revoked & non-expired.
  * `revoke`    — mark a single session revoked (logout from one device).
  * `revoke_all`— revoke every session for a user (logout everywhere).
Expired rows are filtered out at read time; a periodic cleanup job (not in
scope for auth) can delete them.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_session import RefreshSession


async def create(
    db: AsyncSession, *, user_id: int, jti: str, expires_at: datetime
) -> RefreshSession:
    session = RefreshSession(
        jti=jti, user_id=user_id, expires_at=expires_at, revoked=False
    )
    db.add(session)
    await db.flush()
    return session


async def is_valid(db: AsyncSession, jti: str) -> bool:
    stmt = select(RefreshSession).where(RefreshSession.jti == jti)
    session = (await db.execute(stmt)).scalar_one_or_none()
    if session is None or session.revoked:
        return False
    # Compare with UTC then make naive-comparable: server_default may produce
    # tz-naive datetimes on some drivers; coerce both to UTC-naive.
    now = datetime.now(tz=timezone.utc)
    expires = session.expires_at
    if expires.tzinfo is None:
        # treat naive as UTC
        return expires > now.replace(tzinfo=None)
    return expires > now


async def revoke(db: AsyncSession, jti: str) -> None:
    await db.execute(
        update(RefreshSession).where(RefreshSession.jti == jti).values(revoked=True)
    )


async def revoke_all_for_user(db: AsyncSession, user_id: int) -> int:
    """Revoke all active sessions for a user. Returns the count affected."""
    result = await db.execute(
        update(RefreshSession)
        .where(RefreshSession.user_id == user_id, RefreshSession.revoked == False)  # noqa: E712
        .values(revoked=True)
    )
    return result.rowcount or 0


async def purge_expired(db: AsyncSession) -> int:
    """Delete expired rows. Intended for a periodic cleanup task."""
    now = datetime.now(tz=timezone.utc)
    result = await db.execute(
        delete(RefreshSession).where(RefreshSession.expires_at < now)
    )
    return result.rowcount or 0


__all__ = ["create", "is_valid", "revoke", "revoke_all_for_user", "purge_expired"]

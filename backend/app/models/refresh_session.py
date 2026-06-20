"""RefreshSession ORM model.

A refresh token's `jti` (JWT ID) is persisted here so that we can:
  * Validate that a refresh token has not been revoked (logout).
  * Support rotation + revocation (replacing a refresh token issues a new row
    and deletes the old one).
This is what makes logout actually invalidate sessions server-side rather
than only clearing the client cookie.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class RefreshSession(Base):
    """A single refresh-token session for a user."""

    __tablename__ = "refresh_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # The `jti` claim of the refresh JWT. Unique, indexed for fast lookup.
    jti: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # ---- Relationships ----------------------------------------------------
    user: Mapped["User"] = relationship(back_populates="refresh_sessions")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<RefreshSession jti={self.jti!r} user_id={self.user_id} revoked={self.revoked}>"

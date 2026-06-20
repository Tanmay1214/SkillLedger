"""User ORM model."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.refresh_session import RefreshSession


class User(Base):
    """A SkillLedger user, sourced from GitHub OAuth.

    `github_id` is the immutable identity: a GitHub account maps to exactly
    one row here. `access_token` stores the GitHub OAuth token used to call
    the GitHub API on the user's behalf; it is stored encrypted-at-rest in
    production (see TODO in services).
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    github_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, index=True, nullable=False
    )
    username: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), index=True, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    profile_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    access_token: Mapped[str | None] = mapped_column(String(512), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ---- Relationships ----------------------------------------------------
    refresh_sessions: Mapped[List["RefreshSession"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<User id={self.id} username={self.username!r} github_id={self.github_id}>"

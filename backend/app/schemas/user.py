"""User-related schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl


class GithubProfile(BaseModel):
    """Raw profile shape returned by the GitHub `/user` API.

    Only the fields we consume are typed. Extra fields are ignored.
    """

    model_config = ConfigDict(extra="ignore")

    id: int = Field(..., description="GitHub's immutable numeric user ID")
    login: str = Field(..., description="GitHub username")
    name: str | None = None
    email: str | None = None
    avatar_url: HttpUrl | None = None
    html_url: HttpUrl | None = None


class UserPublic(BaseModel):
    """User as exposed over the API — never leaks `access_token`."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    github_id: int
    username: str
    name: str | None = None
    email: EmailStr | None = None
    avatar_url: HttpUrl | None = None
    profile_url: HttpUrl | None = None
    created_at: datetime
    updated_at: datetime


__all__ = ["GithubProfile", "UserPublic"]

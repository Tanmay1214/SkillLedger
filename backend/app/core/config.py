"""Application settings.

All configuration is loaded from environment variables via Pydantic Settings.
Secrets are never hard-coded and never exposed to the frontend.
"""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- Environment ----
    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")

    # ---- Database ----
    database_url: str

    # ---- GitHub OAuth ----
    github_client_id: str
    github_client_secret: str
    github_authorize_url: str = "https://github.com/login/oauth/authorize"
    github_token_url: str = "https://github.com/login/oauth/access_token"
    github_api_url: str = "https://api.github.com"

    # ---- JWT ----
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 30

    # ---- Cookies / Session ----
    session_cookie_name: str = "skillledger_session"
    refresh_cookie_name: str = "skillledger_refresh"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"

    # ---- URLs ----
    frontend_url: AnyHttpUrl
    backend_url: AnyHttpUrl

    # ---- CORS ----
    cors_origins: List[str] | str = Field(default_factory=list)

    # ---- AI / Gemini ----
    gemini_api_key: str | None = Field(default=None)
    glm_api_key: str | None = Field(default=None)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors(cls, v: object) -> object:
        """Allow CORS_ORIGINS to be a comma-separated string in .env."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def cookie_https_only(self) -> bool:
        """Cookies are only marked Secure in production (requires HTTPS)."""
        return self.cookie_secure or self.is_production


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor (use as a FastAPI dependency)."""
    return Settings()  # type: ignore[call-arg]


settings = get_settings()

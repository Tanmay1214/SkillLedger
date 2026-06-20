"""Standardized error response schema."""
from __future__ import annotations

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Consistent JSON error body for all error responses."""

    detail: str
    error_code: str | None = None


__all__ = ["ErrorResponse"]

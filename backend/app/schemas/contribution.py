from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ContributorPublic(BaseModel):
    """Schema representing detailed contributor statistics."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    repository_id: int
    github_user_id: Optional[int] = None
    username: str
    avatar_url: Optional[str] = None
    commits: int = Field(..., validation_alias="commits", serialization_alias="total_commits")
    additions: int = Field(..., validation_alias="additions", serialization_alias="lines_added")
    deletions: int = Field(..., validation_alias="deletions", serialization_alias="lines_deleted")
    ownership_percentage: float
    activity_score: Optional[int] = 0
    created_at: Optional[datetime] = None


class ModuleOwnershipPublic(BaseModel):
    """Schema representing code ownership for a specific logical module."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    repository_id: int
    username: str
    module_name: str
    ownership_percentage: float


class ModuleReportItem(BaseModel):
    """Sub-item representing module ownership inside the final report."""

    module: str
    ownership: int


class ContributionReportResponse(BaseModel):
    """Response of GET /contributions/{repository_id}."""

    model_config = ConfigDict(from_attributes=True)

    primary_contributor: str
    ownership_score: int
    activity_score: int
    confidence: int
    modules: List[ModuleReportItem]
    summary: str


class ContributionProcessResponse(BaseModel):
    """Response of POST /contributions/analyze/{repository_id}."""

    status: str = "processing"

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class SkillResponse(BaseModel):
    """Schema representing an extracted developer skill."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    repository_id: int
    skill_name: str
    confidence_score: int
    category: str
    evidence: List[str]
    created_at: datetime


class ProjectInsightResponse(BaseModel):
    """Schema representing high-level repository insights for recruiters."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    repository_id: int
    project_type: str
    project_category: List[str]
    project_summary: str
    technical_summary: str
    complexity_level: str
    created_at: datetime


class SkillExtractionResponse(BaseModel):
    """Response of POST /skills/extract/{repository_id}."""

    status: str = "processing"

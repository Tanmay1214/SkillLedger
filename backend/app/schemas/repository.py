from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class GithubRepoPublic(BaseModel):
    """Shape of a single repository returned by the GitHub fetch API."""

    github_id: int
    name: str
    owner: str
    private: bool
    language: Optional[str] = None
    stars: int


class GithubRepoListResponse(BaseModel):
    """Response of GET /repositories/github."""

    repositories: List[GithubRepoPublic]


class RepositoryImportRequest(BaseModel):
    """Payload of POST /repositories/import."""

    github_repo_id: int


class RepositoryImportResponse(BaseModel):
    """Response of POST /repositories/import."""

    repository_id: int
    status: str = "queued"


class RepositoryPublic(BaseModel):
    """Metadata of an imported repository (similar to /repositories/{id})."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    github_repo_id: int
    name: str
    owner: str
    repo_url: str
    description: Optional[str] = None
    stars: int
    forks: int
    watchers: int
    default_branch: str
    language: Optional[str] = None
    homepage: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class LanguageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    language_name: str
    percentage: float


class FrameworkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    framework_name: str


class DependencyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    dependency_name: str
    version: str


class ContributorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    github_user_id: Optional[int] = None
    username: str
    commits: int
    additions: int
    deletions: int
    ownership_percentage: float


class RepositoryAnalysisReport(BaseModel):
    """Response of GET /repositories/{id}/analysis."""

    model_config = ConfigDict(from_attributes=True)

    repository: RepositoryPublic
    languages: List[LanguageResponse]
    frameworks: List[FrameworkResponse]
    dependencies: List[DependencyResponse]
    contributors: List[ContributorResponse]

    complexity_score: Optional[int] = None
    security_score: Optional[int] = None
    documentation_score: Optional[int] = None
    analysis_status: str

    # Raw metrics for GLM-5.1 compatibility
    complexity: Optional[dict] = Field(None, alias="complexity_metrics")
    security: Optional[List[dict]] = Field(None, alias="security_findings")
    documentation: Optional[dict] = Field(None, alias="documentation_report")
    commits_info: Optional[dict] = Field(None, alias="commits_metrics")

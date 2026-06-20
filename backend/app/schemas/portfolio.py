"""
Pydantic schemas for the Portfolio Generator API.
"""
from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel


class PortfolioSkill(BaseModel):
    skill_name: str
    category: str
    confidence_score: int

    model_config = {"from_attributes": True}


class SkillGroup(BaseModel):
    category: str
    skills: List[PortfolioSkill]


class PortfolioDeployment(BaseModel):
    deployment_url: str
    provider: Optional[str] = None
    reachable: bool
    deployment_score: int
    ssl_enabled: bool

    model_config = {"from_attributes": True}


class PortfolioProject(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    repo_url: str
    language: Optional[str] = None
    stars: int
    forks: int
    # Scores
    build_score: Optional[int] = None
    proof_score: Optional[int] = None
    complexity_score: Optional[int] = None
    security_score: Optional[int] = None
    documentation_score: Optional[int] = None
    # Contribution
    contribution_percentage: Optional[float] = None
    contribution_summary: Optional[str] = None
    primary_contributor: Optional[str] = None
    # Deployment
    deployment_url: Optional[str] = None
    deployment_reachable: Optional[bool] = None
    deployment_score: Optional[int] = None
    provider: Optional[str] = None
    # Insights
    project_type: Optional[str] = None
    complexity_level: Optional[str] = None
    project_summary: Optional[str] = None
    technical_summary: Optional[str] = None
    project_categories: List[str] = []
    # Skills
    skills: List[PortfolioSkill] = []
    frameworks: List[str] = []


class PortfolioHeader(BaseModel):
    username: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    github_url: str
    repositories_verified: int
    avg_build_score: float
    avg_proof_score: float


class VerificationSummary(BaseModel):
    repositories_analyzed: int
    deployments_verified: int
    verified_skills_count: int
    primary_contributor_projects: int


class PortfolioResponse(BaseModel):
    header: PortfolioHeader
    verification_summary: VerificationSummary
    skill_groups: List[SkillGroup]
    projects: List[PortfolioProject]

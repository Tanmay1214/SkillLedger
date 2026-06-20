from __future__ import annotations

from datetime import datetime
from typing import List, TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Float, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    github_repo_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    repo_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    description: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    stars: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    forks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    watchers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    default_branch: Mapped[str] = mapped_column(String(255), default="main", nullable=False)
    language: Mapped[str | None] = mapped_column(String(255), nullable=True)
    homepage: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    analyses: Mapped[List[RepositoryAnalysis]] = relationship(
        back_populates="repository", cascade="all, delete-orphan", lazy="selectin"
    )
    languages: Mapped[List[Language]] = relationship(
        back_populates="repository", cascade="all, delete-orphan", lazy="selectin"
    )
    frameworks: Mapped[List[Framework]] = relationship(
        back_populates="repository", cascade="all, delete-orphan", lazy="selectin"
    )
    dependencies: Mapped[List[Dependency]] = relationship(
        back_populates="repository", cascade="all, delete-orphan", lazy="selectin"
    )
    contributors: Mapped[List[Contributor]] = relationship(
        back_populates="repository", cascade="all, delete-orphan", lazy="selectin"
    )
    deployment_reports: Mapped[List[DeploymentReport]] = relationship(
        back_populates="repository", cascade="all, delete-orphan", lazy="selectin"
    )
    skills: Mapped[List[Skill]] = relationship(
        back_populates="repository", cascade="all, delete-orphan", lazy="selectin"
    )
    project_insights: Mapped[List[ProjectInsight]] = relationship(
        back_populates="repository", cascade="all, delete-orphan", lazy="selectin"
    )
    contribution_reports: Mapped[List[ContributionReport]] = relationship(
        back_populates="repository", cascade="all, delete-orphan", lazy="selectin"
    )
    module_ownerships: Mapped[List[ModuleOwnership]] = relationship(
        back_populates="repository", cascade="all, delete-orphan", lazy="selectin"
    )


class RepositoryAnalysis(Base):
    __tablename__ = "repository_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    complexity_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    security_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    documentation_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Status: queued, cloning, analyzing, completed, failed
    analysis_status: Mapped[str] = mapped_column(String(50), default="queued", nullable=False)
    
    # Stores the raw JSON results for GLM-5.1 compatibility
    metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    findings: Mapped[list | None] = mapped_column(JSON, nullable=True)
    commits_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    doc_report: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    repository: Mapped[Repository] = relationship(back_populates="analyses")


class Language(Base):
    __tablename__ = "languages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    language_name: Mapped[str] = mapped_column(String(255), nullable=False)
    percentage: Mapped[float] = mapped_column(Float, nullable=False)

    repository: Mapped[Repository] = relationship(back_populates="languages")


class Framework(Base):
    __tablename__ = "frameworks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    framework_name: Mapped[str] = mapped_column(String(255), nullable=False)

    repository: Mapped[Repository] = relationship(back_populates="frameworks")


class Dependency(Base):
    __tablename__ = "dependencies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dependency_name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(100), nullable=False)

    repository: Mapped[Repository] = relationship(back_populates="dependencies")


class Contributor(Base):
    __tablename__ = "contributors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    github_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    commits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    additions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    deletions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ownership_percentage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    activity_score: Mapped[int | None] = mapped_column(Integer, default=0, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )

    repository: Mapped[Repository] = relationship(back_populates="contributors")


class DeploymentReport(Base):
    __tablename__ = "deployment_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    deployment_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    reachable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    ssl_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ssl_expiry_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    security_headers_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    asset_health_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    internal_link_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    deployment_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    repository: Mapped[Repository] = relationship(back_populates="deployment_reports")


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_name: Mapped[str] = mapped_column(String(255), nullable=False)
    confidence_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    evidence: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    repository: Mapped[Repository] = relationship(back_populates="skills")


class ProjectInsight(Base):
    __tablename__ = "project_insights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_type: Mapped[str] = mapped_column(String(255), nullable=False)
    project_category: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    project_summary: Mapped[str] = mapped_column(String(4096), nullable=False)
    technical_summary: Mapped[str] = mapped_column(String(4096), nullable=False)
    complexity_level: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    repository: Mapped[Repository] = relationship(back_populates="project_insights")


class ContributionReport(Base):
    __tablename__ = "contribution_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    primary_contributor: Mapped[str] = mapped_column(String(255), nullable=False)
    ownership_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    activity_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    contribution_summary: Mapped[str] = mapped_column(String(4096), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    repository: Mapped[Repository] = relationship(back_populates="contribution_reports")


class ModuleOwnership(Base):
    __tablename__ = "module_ownerships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    module_name: Mapped[str] = mapped_column(String(255), nullable=False)
    ownership_percentage: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    repository: Mapped[Repository] = relationship(back_populates="module_ownerships")


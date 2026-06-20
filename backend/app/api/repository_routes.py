from __future__ import annotations

import logging
from typing import Annotated, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth.dependencies import CurrentUser
from app.database.session import get_db
from app.models.repository import Repository, RepositoryAnalysis
from app.schemas.repository import (
    GithubRepoListResponse,
    GithubRepoPublic,
    RepositoryImportRequest,
    RepositoryImportResponse,
    RepositoryPublic,
    RepositoryAnalysisReport,
    LanguageResponse,
    FrameworkResponse,
    DependencyResponse,
    ContributorResponse,
)
from app.services.github_service import fetch_user_repositories
from app.services.github_import_service import import_github_repository
from app.services.analysis_service import run_analysis_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/repositories", tags=["repositories"])


@router.get(
    "/github",
    response_model=GithubRepoListResponse,
    summary="List all repositories from the user's GitHub account",
)
async def list_github_repositories(
    current_user: CurrentUser,
) -> GithubRepoListResponse:
    """Fetch the list of repositories from GitHub for the authenticated user."""
    if not current_user.access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User does not have a linked GitHub access token.",
        )
    
    try:
        repos = await fetch_user_repositories(current_user.access_token)
        github_repos = []
        for r in repos:
            # Map GitHub API structure to GithubRepoPublic schema
            github_repos.append(
                GithubRepoPublic(
                    github_id=r["id"],
                    name=r["name"],
                    owner=r["owner"]["login"],
                    private=r.get("private", False),
                    language=r.get("language"),
                    stars=r.get("stargazers_count", 0),
                )
            )
        return GithubRepoListResponse(repositories=github_repos)
    except Exception as e:
        logger.exception("Failed to fetch user repositories from GitHub")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch repositories from GitHub: {str(e)}",
        )


@router.post(
    "/import",
    response_model=RepositoryImportResponse,
    summary="Import a GitHub repository and queue code analysis",
)
async def import_repository(
    current_user: CurrentUser,
    request: RepositoryImportRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RepositoryImportResponse:
    """Imports repository metadata from GitHub and queues a background task

    to perform static analysis (cyclomatic complexity, security, dependencies, documentation).
    """
    if not current_user.access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User does not have a linked GitHub access token.",
        )

    try:
        # 1. Import repository metadata and languages breakdown
        repo = await import_github_repository(
            db=db,
            user_id=current_user.id,
            access_token=current_user.access_token,
            github_repo_id=request.github_repo_id,
        )
        
        # 2. Create a RepositoryAnalysis entry in the database
        # Check if there's an ongoing analysis to avoid duplicate tasks
        analysis_stmt = select(RepositoryAnalysis).where(
            RepositoryAnalysis.repository_id == repo.id,
            RepositoryAnalysis.analysis_status.in_(["queued", "cloning", "analyzing"])
        ).order_by(RepositoryAnalysis.created_at.desc())
        
        analysis_res = await db.execute(analysis_stmt)
        existing_analysis = analysis_res.scalars().first()
        
        if existing_analysis:
            # Re-use or return the current active analysis
            return RepositoryImportResponse(
                repository_id=repo.id,
                status=existing_analysis.analysis_status,
            )

        # Create new analysis task
        analysis = RepositoryAnalysis(
            repository_id=repo.id,
            analysis_status="queued",
        )
        db.add(analysis)
        await db.commit()
        await db.refresh(analysis)

        # 3. Add task to background tasks
        background_tasks.add_task(
            run_analysis_pipeline,
            repository_id=repo.id,
            analysis_id=analysis.id,
            repo_url=repo.repo_url,
            access_token=current_user.access_token,
        )

        return RepositoryImportResponse(
            repository_id=repo.id,
            status=analysis.analysis_status,
        )
    except Exception as e:
        logger.exception("Failed to import repository")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import and analyze repository: {str(e)}",
        )


@router.get(
    "",
    response_model=List[RepositoryPublic],
    summary="List all repositories imported by the user",
)
async def list_imported_repositories(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> List[RepositoryPublic]:
    """Retrieve all repositories that the user has imported into SkillLedger."""
    stmt = select(Repository).where(Repository.user_id == current_user.id).order_by(Repository.name.asc())
    res = await db.execute(stmt)
    repos = res.scalars().all()
    return [RepositoryPublic.model_validate(r) for r in repos]


@router.get(
    "/{id}",
    response_model=RepositoryPublic,
    summary="Get repository metadata by ID",
)
async def get_repository(
    id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RepositoryPublic:
    """Fetch metadata for a specific imported repository."""
    stmt = select(Repository).where(Repository.id == id, Repository.user_id == current_user.id)
    res = await db.execute(stmt)
    repo = res.scalars().first()
    
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found or access denied.",
        )
    return RepositoryPublic.model_validate(repo)


@router.get(
    "/{id}/analysis",
    response_model=RepositoryAnalysisReport,
    summary="Retrieve the compiled repository analysis report",
)
async def get_repository_analysis(
    id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RepositoryAnalysisReport:
    """Retrieve the details, languages, frameworks, dependencies, and contributor

    breakdowns, along with static analysis reports for the repository.
    """
    # 1. Fetch repository and verify ownership
    stmt = select(Repository).where(Repository.id == id, Repository.user_id == current_user.id)
    res = await db.execute(stmt)
    repo = res.scalars().first()
    
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found or access denied.",
        )
        
    # 2. Fetch the latest analysis report
    analysis_stmt = select(RepositoryAnalysis).where(
        RepositoryAnalysis.repository_id == id
    ).order_by(RepositoryAnalysis.created_at.desc())
    analysis_res = await db.execute(analysis_stmt)
    latest_analysis = analysis_res.scalars().first()
    
    # 3. Construct unified response
    return RepositoryAnalysisReport(
        repository=RepositoryPublic.model_validate(repo),
        languages=[LanguageResponse.model_validate(l) for l in repo.languages],
        frameworks=[FrameworkResponse.model_validate(f) for f in repo.frameworks],
        dependencies=[DependencyResponse.model_validate(d) for d in repo.dependencies],
        contributors=[ContributorResponse.model_validate(c) for c in repo.contributors],
        complexity_score=latest_analysis.complexity_score if latest_analysis else None,
        security_score=latest_analysis.security_score if latest_analysis else None,
        documentation_score=latest_analysis.documentation_score if latest_analysis else None,
        analysis_status=latest_analysis.analysis_status if latest_analysis else "not_started",
        complexity_metrics=latest_analysis.metrics if latest_analysis else None,
        security_findings=latest_analysis.findings if latest_analysis else None,
        documentation_report=latest_analysis.doc_report if latest_analysis else None,
        commits_metrics=latest_analysis.commits_info if latest_analysis else None,
    )

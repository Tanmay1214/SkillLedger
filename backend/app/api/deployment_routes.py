from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth.dependencies import CurrentUser
from app.database.session import get_db
from app.models.repository import Repository, DeploymentReport
from app.schemas.deployment import DeploymentDiscoverResponse, DeploymentReportResponse
from app.services.deployment_discovery import discover_deployment_url
from app.services.deployment_verification import run_deployment_verification

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/deployments", tags=["deployments"])


@router.post(
    "/discover/{repository_id}",
    response_model=DeploymentDiscoverResponse,
    summary="Automatically discover repository deployment URL",
)
async def discover_repository_deployment(
    repository_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeploymentDiscoverResponse:
    """Uses GitHub API metadata, Pages settings, and README scanning

    to discover the live deployment URL. If found, updates the Repository.homepage.
    """
    stmt = select(Repository).where(Repository.id == repository_id, Repository.user_id == current_user.id)
    res = await db.execute(stmt)
    repo = res.scalars().first()
    
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found or access denied.",
        )
        
    if not current_user.access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User does not have a linked GitHub access token.",
        )
        
    discovery = await discover_deployment_url(current_user.access_token, repo.github_repo_id)
    url = discovery.get("deployment_url")
    
    if url:
        # Save home URL on repository model
        repo.homepage = url
        await db.commit()
        await db.refresh(repo)
        
    return DeploymentDiscoverResponse(
        deployment_url=url,
        source=discovery.get("source"),
    )


@router.post(
    "/verify/{repository_id}",
    response_model=DeploymentReportResponse,
    summary="Execute deployment verification scan",
)
async def verify_repository_deployment(
    repository_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    url: Annotated[str | None, Query(description="Optional custom deployment URL to verify")] = None,
) -> DeploymentReportResponse:
    """Performs full reachability, SSL, security headers, BS4 content health,

    broken assets, internal links, and Gemini AI consistency checks on the deployment.
    """
    stmt = select(Repository).where(Repository.id == repository_id, Repository.user_id == current_user.id)
    res = await db.execute(stmt)
    repo = res.scalars().first()
    
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found or access denied.",
        )
        
    # Determine which URL to verify: custom passed query param, or repository homepage
    target_url = url or repo.homepage
    if not target_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "No deployment URL available. Discover one first or pass it manually "
                "via the 'url' query parameter."
            ),
        )
        
    # Clean the URL structure
    target_url = target_url.strip()
    if not target_url.startswith(("http://", "https://")):
        target_url = "https://" + target_url

    try:
        # Run verification checks synchronously since it takes a few seconds and returns report
        report = await run_deployment_verification(repository_id, target_url)
        return DeploymentReportResponse.model_validate(report)
    except Exception as e:
        logger.exception("Deployment verification pipeline execution failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verification failed: {str(e)}",
        )


@router.get(
    "/report/{repository_id}",
    response_model=DeploymentReportResponse,
    summary="Get the latest deployment verification report",
)
async def get_latest_deployment_report(
    repository_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeploymentReportResponse:
    """Fetch the latest deployment report for the specified repository."""
    # Verify repository ownership
    repo_stmt = select(Repository).where(Repository.id == repository_id, Repository.user_id == current_user.id)
    repo_res = await db.execute(repo_stmt)
    repo = repo_res.scalars().first()
    
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found or access denied.",
        )
        
    # Get latest deployment report
    stmt = select(DeploymentReport).where(
        DeploymentReport.repository_id == repository_id
    ).order_by(DeploymentReport.created_at.desc())
    res = await db.execute(stmt)
    report = res.scalars().first()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No deployment report found for this repository.",
        )
        
    return DeploymentReportResponse.model_validate(report)

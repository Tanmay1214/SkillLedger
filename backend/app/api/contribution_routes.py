from __future__ import annotations

import logging
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth.dependencies import CurrentUser
from app.database.session import get_db, async_session_factory
from app.models.repository import Repository, Contributor, ContributionReport, ModuleOwnership
from app.schemas.contribution import (
    ContributorPublic,
    ModuleOwnershipPublic,
    ContributionReportResponse,
    ContributionProcessResponse,
    ModuleReportItem
)
from app.services.contribution_verification_service import ContributionVerificationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contributions", tags=["contributions"])


async def run_contributions_background(repository_id: int) -> None:
    """Background task to run git contribution analytics and save details."""
    try:
        async with async_session_factory() as session:
            await ContributionVerificationService.verify_and_save_contributions(session, repository_id)
    except Exception as e:
        logger.exception(f"Background contribution analysis failed for repo {repository_id}: {e}")


@router.post(
    "/analyze/{repository_id}",
    response_model=ContributionProcessResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger repository contribution verification scan",
)
async def analyze_contributions(
    repository_id: int,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ContributionProcessResponse:
    """Clones repository, aggregates git timeline metrics, and generates code ownership summaries."""
    stmt = select(Repository).where(Repository.id == repository_id, Repository.user_id == current_user.id)
    res = await db.execute(stmt)
    repo = res.scalars().first()
    
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found or access denied.",
        )
        
    background_tasks.add_task(run_contributions_background, repository_id)
    return ContributionProcessResponse(status="processing")


@router.get(
    "/{repository_id}",
    response_model=ContributionReportResponse,
    summary="Retrieve repository contribution report",
)
async def get_contribution_report(
    repository_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ContributionReportResponse:
    """Fetches the compiled contribution score, activity index, owned modules, and GLM summary."""
    stmt = select(Repository).where(Repository.id == repository_id, Repository.user_id == current_user.id)
    res = await db.execute(stmt)
    repo = res.scalars().first()
    
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found or access denied.",
        )
        
    rep_stmt = select(ContributionReport).where(ContributionReport.repository_id == repository_id)
    rep_res = await db.execute(rep_stmt)
    report = rep_res.scalars().first()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No contribution report found for this repository. Run analysis first.",
        )

    # Fetch module ownerships for primary contributor
    mod_stmt = (
        select(ModuleOwnership)
        .where(ModuleOwnership.repository_id == repository_id)
        .where(ModuleOwnership.username == report.primary_contributor)
    )
    mod_res = await db.execute(mod_stmt)
    modules = mod_res.scalars().all()
    
    # Map to schema output model
    module_items = [
        ModuleReportItem(
            module=m.module_name,
            ownership=int(round(m.ownership_percentage))
        )
        for m in modules
    ]
    
    # Calculate a dynamic confidence score: if ownership is high, confidence is high
    confidence = min(98, int(round(report.ownership_score * 0.9 + 10)))
    confidence = max(20, confidence)
    
    return ContributionReportResponse(
        primary_contributor=report.primary_contributor,
        ownership_score=report.ownership_score,
        activity_score=report.activity_score,
        confidence=confidence,
        modules=module_items,
        summary=report.contribution_summary
    )


@router.get(
    "/{repository_id}/contributors",
    response_model=List[ContributorPublic],
    summary="Retrieve all repository contributors",
)
async def get_contributors(
    repository_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> List[Contributor]:
    """Returns a list of all commit authors with their normalized code activity statistics."""
    stmt = select(Repository).where(Repository.id == repository_id, Repository.user_id == current_user.id)
    res = await db.execute(stmt)
    repo = res.scalars().first()
    
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found or access denied.",
        )
        
    cont_stmt = select(Contributor).where(Contributor.repository_id == repository_id).order_by(Contributor.commits.desc())
    cont_res = await db.execute(cont_stmt)
    return list(cont_res.scalars().all())


@router.get(
    "/{repository_id}/ownership",
    response_model=List[ModuleOwnershipPublic],
    summary="Retrieve module ownership breakdown",
)
async def get_ownership_breakdown(
    repository_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> List[ModuleOwnership]:
    """Returns granular file ownership grouped by logical codebase modules."""
    stmt = select(Repository).where(Repository.id == repository_id, Repository.user_id == current_user.id)
    res = await db.execute(stmt)
    repo = res.scalars().first()
    
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found or access denied.",
        )
        
    mod_stmt = select(ModuleOwnership).where(ModuleOwnership.repository_id == repository_id).order_by(ModuleOwnership.ownership_percentage.desc())
    mod_res = await db.execute(mod_stmt)
    return list(mod_res.scalars().all())

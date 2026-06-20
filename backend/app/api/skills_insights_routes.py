from __future__ import annotations

import logging
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth.dependencies import CurrentUser
from app.database.session import get_db, async_session_factory
from app.models.repository import Repository, RepositoryAnalysis, Skill, ProjectInsight
from app.schemas.skills_insights import SkillResponse, ProjectInsightResponse, SkillExtractionResponse
from app.services.skill_extraction_service import SkillExtractionService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["skills_insights"])


async def run_extraction_background(repository_id: int) -> None:
    """Background worker to run skill extraction within a clean database session context."""
    logger.info(f"Background task triggered: Extracting skills for repository {repository_id}")
    try:
        async with async_session_factory() as session:
            await SkillExtractionService.extract_and_save_skills(session, repository_id)
    except Exception as e:
        logger.exception(f"Error in background skill extraction for repo {repository_id}: {e}")


@router.post(
    "/skills/extract/{repository_id}",
    response_model=SkillExtractionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger GLM skill extraction process",
)
async def extract_skills(
    repository_id: int,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SkillExtractionResponse:
    """Analyzes repository metadata and code statistics via GLM or rule-based models in a background task."""
    stmt = select(Repository).where(Repository.id == repository_id, Repository.user_id == current_user.id)
    res = await db.execute(stmt)
    repo = res.scalars().first()
    
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found or access denied.",
        )

    # Make sure we have a completed analysis report
    analysis_stmt = (
        select(RepositoryAnalysis)
        .where(RepositoryAnalysis.repository_id == repository_id)
        .where(RepositoryAnalysis.analysis_status == "completed")
    )
    analysis_res = await db.execute(analysis_stmt)
    analysis = analysis_res.scalars().first()
    
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Repository analysis must be completed successfully before extracting skills.",
        )

    background_tasks.add_task(run_extraction_background, repository_id)
    return SkillExtractionResponse(status="processing")


@router.get(
    "/skills/{repository_id}",
    response_model=List[SkillResponse],
    summary="Retrieve extracted skills",
)
async def get_skills(
    repository_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> List[Skill]:
    """Returns a list of verified skills extracted for the given repository."""
    stmt = select(Repository).where(Repository.id == repository_id, Repository.user_id == current_user.id)
    res = await db.execute(stmt)
    repo = res.scalars().first()
    
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found or access denied.",
        )
        
    skills_stmt = select(Skill).where(Skill.repository_id == repository_id).order_by(Skill.confidence_score.desc())
    skills_res = await db.execute(skills_stmt)
    return list(skills_res.scalars().all())


@router.get(
    "/insights/{repository_id}",
    response_model=ProjectInsightResponse,
    summary="Retrieve project recruiter insights",
)
async def get_project_insights(
    repository_id: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProjectInsight:
    """Returns recruiter-friendly project summaries, tech summaries, complexity and category classifications."""
    stmt = select(Repository).where(Repository.id == repository_id, Repository.user_id == current_user.id)
    res = await db.execute(stmt)
    repo = res.scalars().first()
    
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found or access denied.",
        )
        
    insight_stmt = (
        select(ProjectInsight)
        .where(ProjectInsight.repository_id == repository_id)
        .order_by(ProjectInsight.created_at.desc())
    )
    insight_res = await db.execute(insight_stmt)
    insight = insight_res.scalars().first()
    
    if not insight:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No project insights found for this repository. Please run skill extraction first.",
        )
        
    return insight

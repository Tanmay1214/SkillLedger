"""
Portfolio API routes — public endpoints to serve developer portfolios.

GET /portfolio/{username}           → full portfolio
GET /portfolio/{username}/projects  → projects list
GET /portfolio/{username}/skills    → aggregated skill groups
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.portfolio import PortfolioResponse, PortfolioProject, SkillGroup
from app.services.portfolio_service import PortfolioService
from typing import List

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("/{username}", response_model=PortfolioResponse, summary="Get full portfolio for a user")
async def get_portfolio(username: str, db: AsyncSession = Depends(get_db)):
    """
    Returns the complete public portfolio for a given GitHub username.
    Aggregates: repositories, skills, project insights, contribution
    reports, and deployment reports into a single response.
    """
    portfolio = await PortfolioService.get_portfolio(db, username)
    if portfolio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No portfolio found for user '{username}'",
        )
    return portfolio


@router.get("/{username}/projects", response_model=List[PortfolioProject], summary="Get projects for a user")
async def get_projects(username: str, db: AsyncSession = Depends(get_db)):
    """Returns a list of verified projects for the given username."""
    projects = await PortfolioService.get_projects(db, username)
    if projects is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No portfolio found for user '{username}'",
        )
    return projects


@router.get("/{username}/skills", response_model=List[SkillGroup], summary="Get skills for a user")
async def get_skills(username: str, db: AsyncSession = Depends(get_db)):
    """Returns grouped, deduplicated skills for the given username."""
    skills = await PortfolioService.get_skills(db, username)
    if skills is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No portfolio found for user '{username}'",
        )
    return skills

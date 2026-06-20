"""Aggregates all API routers under the /api/v1 prefix."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.auth_routes import router as auth_router
from app.api.repository_routes import router as repository_router
from app.api.deployment_routes import router as deployment_router
from app.api.skills_insights_routes import router as skills_insights_router
from app.api.contribution_routes import router as contribution_router
from app.api.portfolio_routes import router as portfolio_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(repository_router)
api_router.include_router(deployment_router)
api_router.include_router(skills_insights_router)
api_router.include_router(contribution_router)
api_router.include_router(portfolio_router)


__all__ = ["api_router"]


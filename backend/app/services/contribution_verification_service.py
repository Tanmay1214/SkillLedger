from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import async_session_factory
from app.models.repository import Repository, Contributor, ContributionReport, ModuleOwnership
from app.services.clone_service import clone_repository, cleanup_repository
from app.services.commit_analysis_service import CommitAnalysisService
from app.services.contributor_analysis_service import ContributorAnalysisService
from app.services.ownership_engine import OwnershipEngine
from app.services.glm_contribution_summary import GLMContributionSummary
from app.models.user import User

logger = logging.getLogger(__name__)


class ContributionVerificationService:
    """Orchestrator to clone, analyze git histories, compute module ownership, and write contribution reports."""

    @classmethod
    async def verify_and_save_contributions(
        cls,
        db: AsyncSession,
        repository_id: int,
    ) -> Optional[ContributionReport]:
        """Triggers full contribution analytics: clones the repo, calculates ownership, writes data, and returns report."""
        logger.info(f"Triggering contribution verification process for repository_id={repository_id}")
        
        # 1. Fetch Repository
        repo_stmt = select(Repository).where(Repository.id == repository_id)
        repo_res = await db.execute(repo_stmt)
        repository = repo_res.scalars().first()
        if not repository:
            logger.error(f"Repository {repository_id} not found in database.")
            return None
            
        # 2. Get User Access Token
        user_stmt = select(User).where(User.id == repository.user_id)
        user_res = await db.execute(user_stmt)
        user = user_res.scalars().first()
        access_token = user.access_token if user else None

        # 3. Clone Repository locally to temporary directory
        logger.info(f"Cloning repo URL for analysis: {repository.repo_url}")
        temp_dir = clone_repository(repository.repo_url, access_token)
        
        # 4. Perform scans inside try/finally block to guarantee cleanup
        try:
            # Commit frequency and timeline analytics
            commit_history_stats = CommitAnalysisService.analyze_commit_history(temp_dir)
            
            # Contributor commit and line-level changes
            raw_contributor_data = ContributorAnalysisService.analyze_contributors(temp_dir)
            
            # Module ownership, weighted scores, and overall metrics
            ownership_results = OwnershipEngine.calculate_ownership(raw_contributor_data, commit_history_stats)
        finally:
            # Always clean up cloned folder from disk
            cleanup_repository(temp_dir)

        # 5. Generate GLM Summary Report
        summary = await GLMContributionSummary.generate_contribution_summary(
            primary_contributor=ownership_results["primary_contributor"],
            ownership_score=ownership_results["ownership_score"],
            activity_score=ownership_results["activity_score"],
            modules=ownership_results["modules"],
            total_commits=commit_history_stats["total_commits"]
        )

        # 6. Database updates
        # Clear old database records for report and modules
        rep_del = select(ContributionReport).where(ContributionReport.repository_id == repository_id)
        rep_res = await db.execute(rep_del)
        for r in rep_res.scalars().all():
            await db.delete(r)

        mod_del = select(ModuleOwnership).where(ModuleOwnership.repository_id == repository_id)
        mod_res = await db.execute(mod_del)
        for m in mod_res.scalars().all():
            await db.delete(m)

        # Update contributors details
        # Remove old contributors list to rebuild from new git history
        cont_del = select(Contributor).where(Contributor.repository_id == repository_id)
        cont_res = await db.execute(cont_del)
        for c in cont_res.scalars().all():
            await db.delete(c)

        # Re-insert fresh Git contributors
        for c_data in ownership_results["contributors"]:
            db.add(Contributor(
                repository_id=repository_id,
                github_user_id=c_data["github_user_id"],
                username=c_data["username"],
                avatar_url=c_data["avatar_url"],
                commits=c_data["total_commits"],
                additions=c_data["lines_added"],
                deletions=c_data["lines_deleted"],
                ownership_percentage=c_data["ownership_percentage"],
                activity_score=c_data["activity_score"],
            ))

        # Insert fresh module ownership percentages
        # module_ownerships_grid: module -> username -> percentage
        for mod_name, shares in ownership_results["module_ownerships_grid"].items():
            for username, pct in shares.items():
                if pct > 0:
                    db.add(ModuleOwnership(
                        repository_id=repository_id,
                        username=username,
                        module_name=mod_name,
                        ownership_percentage=pct
                    ))

        # Save final contribution report
        report = ContributionReport(
            repository_id=repository_id,
            primary_contributor=ownership_results["primary_contributor"],
            ownership_score=ownership_results["ownership_score"],
            activity_score=ownership_results["activity_score"],
            contribution_summary=summary[:4096]
        )
        db.add(report)

        await db.commit()
        await db.refresh(report)

        logger.info(f"Successfully processed contributions report for repository {repository_id}. Report ID={report.id}")
        return report

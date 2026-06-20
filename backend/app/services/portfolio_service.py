"""
Portfolio Service — aggregates verified data from all repository modules
to construct a complete developer portfolio.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.repository import (
    Repository,
    RepositoryAnalysis,
    Skill,
    DeploymentReport,
    ContributionReport,
    ProjectInsight,
)
from app.schemas.portfolio import (
    PortfolioHeader,
    PortfolioProject,
    PortfolioSkill,
    SkillGroup,
    PortfolioResponse,
    VerificationSummary,
)

logger = logging.getLogger(__name__)

# ── Score weights ──────────────────────────────────────────────────────────────

def _build_score(
    complexity: Optional[int],
    security: Optional[int],
    documentation: Optional[int],
) -> Optional[int]:
    """40% complexity + 30% security + 30% documentation."""
    if complexity is None and security is None and documentation is None:
        return None
    c = complexity or 0
    s = security or 0
    d = documentation or 0
    return round(0.4 * c + 0.3 * s + 0.3 * d)


def _proof_score(
    deployment_score: Optional[int],
    contribution_pct: Optional[float],
) -> Optional[int]:
    """50% deployment score + 50% contribution percentage."""
    if deployment_score is None and contribution_pct is None:
        return None
    dep = deployment_score or 0
    con = contribution_pct or 0.0
    return round(0.5 * dep + 0.5 * con)


# ── Skill category normalizer ──────────────────────────────────────────────────

_CATEGORY_ORDER = [
    "Programming Language",
    "Framework",
    "Database",
    "Backend",
    "Frontend",
    "Mobile",
    "Cybersecurity",
    "AI/ML",
    "DevOps",
    "Other",
]

def _normalize_category(raw: str) -> str:
    mapping = {
        "language": "Programming Language",
        "programming language": "Programming Language",
        "framework": "Framework",
        "library": "Framework",
        "database": "Database",
        "backend": "Backend",
        "frontend": "Frontend",
        "mobile": "Mobile",
        "security": "Cybersecurity",
        "cybersecurity": "Cybersecurity",
        "ai": "AI/ML",
        "ml": "AI/ML",
        "machine learning": "AI/ML",
        "devops": "DevOps",
        "cloud": "DevOps",
        "infrastructure": "DevOps",
    }
    key = raw.strip().lower()
    for k, v in mapping.items():
        if k in key:
            return v
    return raw.title()


# ── Portfolio Service ──────────────────────────────────────────────────────────

class PortfolioService:

    @staticmethod
    async def get_portfolio(db: AsyncSession, username: str) -> Optional[PortfolioResponse]:
        # 1. Fetch user
        user_stmt = select(User).where(User.username == username)
        user_res = await db.execute(user_stmt)
        user: Optional[User] = user_res.scalars().first()
        if not user:
            return None

        # 2. Fetch all repositories for this user
        repo_stmt = select(Repository).where(Repository.user_id == user.id)
        repo_res = await db.execute(repo_stmt)
        repositories: List[Repository] = list(repo_res.scalars().all())

        if not repositories:
            return PortfolioResponse(
                header=PortfolioHeader(
                    username=user.username,
                    name=user.name,
                    avatar_url=user.avatar_url,
                    github_url=f"https://github.com/{user.username}",
                    repositories_verified=0,
                    avg_build_score=0.0,
                    avg_proof_score=0.0,
                ),
                verification_summary=VerificationSummary(
                    repositories_analyzed=0,
                    deployments_verified=0,
                    verified_skills_count=0,
                    primary_contributor_projects=0,
                ),
                skill_groups=[],
                projects=[],
            )

        repo_ids = [r.id for r in repositories]

        # 3. Fetch all analyses
        analyses_stmt = select(RepositoryAnalysis).where(
            RepositoryAnalysis.repository_id.in_(repo_ids)
        )
        analyses_res = await db.execute(analyses_stmt)
        all_analyses = list(analyses_res.scalars().all())
        # Map: repo_id → latest analysis
        analyses_by_repo: dict[int, RepositoryAnalysis] = {}
        for a in all_analyses:
            existing = analyses_by_repo.get(a.repository_id)
            if existing is None or a.created_at > existing.created_at:
                analyses_by_repo[a.repository_id] = a

        # 4. Fetch all skills
        skills_stmt = select(Skill).where(Skill.repository_id.in_(repo_ids))
        skills_res = await db.execute(skills_stmt)
        all_skills: List[Skill] = list(skills_res.scalars().all())

        # 5. Fetch all deployment reports (latest per repo)
        dep_stmt = select(DeploymentReport).where(
            DeploymentReport.repository_id.in_(repo_ids)
        )
        dep_res = await db.execute(dep_stmt)
        all_deployments = list(dep_res.scalars().all())
        deployments_by_repo: dict[int, DeploymentReport] = {}
        for d in all_deployments:
            existing = deployments_by_repo.get(d.repository_id)
            if existing is None or d.created_at > existing.created_at:
                deployments_by_repo[d.repository_id] = d

        # 6. Fetch contribution reports (latest per repo)
        contrib_stmt = select(ContributionReport).where(
            ContributionReport.repository_id.in_(repo_ids)
        )
        contrib_res = await db.execute(contrib_stmt)
        all_contribs = list(contrib_res.scalars().all())
        contribs_by_repo: dict[int, ContributionReport] = {}
        for cr in all_contribs:
            existing = contribs_by_repo.get(cr.repository_id)
            if existing is None or cr.created_at > existing.created_at:
                contribs_by_repo[cr.repository_id] = cr

        # 7. Fetch project insights (latest per repo)
        insight_stmt = select(ProjectInsight).where(
            ProjectInsight.repository_id.in_(repo_ids)
        )
        insight_res = await db.execute(insight_stmt)
        all_insights = list(insight_res.scalars().all())
        insights_by_repo: dict[int, ProjectInsight] = {}
        for pi in all_insights:
            existing = insights_by_repo.get(pi.repository_id)
            if existing is None or pi.created_at > existing.created_at:
                insights_by_repo[pi.repository_id] = pi

        # 8. Skills by repo
        skills_by_repo: dict[int, List[Skill]] = defaultdict(list)
        for s in all_skills:
            skills_by_repo[s.repository_id].append(s)

        # ── Build project cards ────────────────────────────────────────────────
        projects: List[PortfolioProject] = []
        build_scores: List[int] = []
        proof_scores: List[int] = []
        deployments_verified = 0
        primary_contributor_projects = 0

        for repo in repositories:
            analysis = analyses_by_repo.get(repo.id)
            deployment = deployments_by_repo.get(repo.id)
            contribution = contribs_by_repo.get(repo.id)
            insight = insights_by_repo.get(repo.id)
            repo_skills = skills_by_repo.get(repo.id, [])

            c_score = analysis.complexity_score if analysis else None
            s_score = analysis.security_score if analysis else None
            d_score = analysis.documentation_score if analysis else None
            dep_score = deployment.deployment_score if deployment else None

            # Contribution % — try ContributionReport.ownership_score first
            contrib_pct: Optional[float] = None
            primary = None
            contrib_summary = None
            if contribution:
                contrib_pct = float(contribution.ownership_score)
                primary = contribution.primary_contributor
                contrib_summary = contribution.contribution_summary

            bs = _build_score(c_score, s_score, d_score)
            ps = _proof_score(dep_score, contrib_pct)

            if bs is not None:
                build_scores.append(bs)
            if ps is not None:
                proof_scores.append(ps)

            if deployment and deployment.reachable:
                deployments_verified += 1

            if contribution:
                primary_contributor_projects += 1

            project_skill_list = [
                PortfolioSkill(
                    skill_name=sk.skill_name,
                    category=_normalize_category(sk.category),
                    confidence_score=sk.confidence_score,
                )
                for sk in sorted(repo_skills, key=lambda x: x.confidence_score, reverse=True)
            ]

            framework_names = [fr.framework_name for fr in repo.frameworks]

            projects.append(
                PortfolioProject(
                    id=repo.id,
                    name=repo.name,
                    description=repo.description,
                    repo_url=repo.repo_url,
                    language=repo.language,
                    stars=repo.stars,
                    forks=repo.forks,
                    build_score=bs,
                    proof_score=ps,
                    complexity_score=c_score,
                    security_score=s_score,
                    documentation_score=d_score,
                    contribution_percentage=contrib_pct,
                    contribution_summary=contrib_summary,
                    primary_contributor=primary,
                    deployment_url=deployment.deployment_url if deployment else repo.homepage,
                    deployment_reachable=deployment.reachable if deployment else None,
                    deployment_score=dep_score,
                    provider=deployment.provider if deployment else None,
                    project_type=insight.project_type if insight else None,
                    complexity_level=insight.complexity_level if insight else None,
                    project_summary=insight.project_summary if insight else None,
                    technical_summary=insight.technical_summary if insight else None,
                    project_categories=list(insight.project_category) if insight else [],
                    skills=project_skill_list,
                    frameworks=framework_names,
                )
            )

        # Sort by build_score desc
        projects.sort(key=lambda p: p.build_score or 0, reverse=True)

        # ── Aggregate skills across all repos ──────────────────────────────────
        # Best confidence per (skill_name, normalized_category)
        skill_best: dict[tuple[str, str], int] = {}
        for sk in all_skills:
            cat = _normalize_category(sk.category)
            key = (sk.skill_name.strip(), cat)
            existing = skill_best.get(key, 0)
            if sk.confidence_score > existing:
                skill_best[key] = sk.confidence_score

        grouped: dict[str, List[PortfolioSkill]] = defaultdict(list)
        for (name, cat), conf in skill_best.items():
            grouped[cat].append(PortfolioSkill(skill_name=name, category=cat, confidence_score=conf))

        # Sort each group by confidence desc
        for cat in grouped:
            grouped[cat].sort(key=lambda x: x.confidence_score, reverse=True)

        skill_groups = [
            SkillGroup(category=cat, skills=grouped[cat])
            for cat in _CATEGORY_ORDER
            if cat in grouped
        ]
        # Any leftover categories not in ORDER
        extra_cats = [c for c in grouped if c not in _CATEGORY_ORDER]
        for cat in extra_cats:
            skill_groups.append(SkillGroup(category=cat, skills=grouped[cat]))

        # ── Header stats ───────────────────────────────────────────────────────
        avg_build = round(sum(build_scores) / len(build_scores), 1) if build_scores else 0.0
        avg_proof = round(sum(proof_scores) / len(proof_scores), 1) if proof_scores else 0.0

        header = PortfolioHeader(
            username=user.username,
            name=user.name,
            avatar_url=user.avatar_url,
            github_url=f"https://github.com/{user.username}",
            repositories_verified=len(repositories),
            avg_build_score=avg_build,
            avg_proof_score=avg_proof,
        )

        verification = VerificationSummary(
            repositories_analyzed=len(analyses_by_repo),
            deployments_verified=deployments_verified,
            verified_skills_count=len(skill_best),
            primary_contributor_projects=primary_contributor_projects,
        )

        return PortfolioResponse(
            header=header,
            verification_summary=verification,
            skill_groups=skill_groups,
            projects=projects,
        )

    @staticmethod
    async def get_projects(db: AsyncSession, username: str) -> Optional[List[PortfolioProject]]:
        portfolio = await PortfolioService.get_portfolio(db, username)
        if portfolio is None:
            return None
        return portfolio.projects

    @staticmethod
    async def get_skills(db: AsyncSession, username: str) -> Optional[List[SkillGroup]]:
        portfolio = await PortfolioService.get_portfolio(db, username)
        if portfolio is None:
            return None
        return portfolio.skill_groups

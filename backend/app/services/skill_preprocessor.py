from __future__ import annotations

import base64
import logging
import re
from typing import Any, Dict, List, Optional
import httpx
from sqlalchemy.future import select

from app.core.config import settings
from app.models.repository import Repository, RepositoryAnalysis, Language, Framework, Dependency, Contributor
from app.models.user import User

logger = logging.getLogger(__name__)


class SkillExtractionPreprocessor:
    """Preprocessor for repository intelligence data to create a compact context for LLM extraction."""

    @staticmethod
    def _build_mock_folder_structure(
        languages: List[str], frameworks: List[str], dependencies: List[str]
    ) -> str:
        """Constructs a plausible folder structure based on technologies if GitHub API is unavailable."""
        structure = [
            "├── README.md",
        ]
        
        # Backend python app
        if "Python" in languages:
            structure.extend([
                "├── requirements.txt",
                "├── app/",
                "│   ├── __init__.py",
                "│   ├── main.py",
                "│   ├── api/",
                "│   │   ├── router.py",
                "│   │   └── endpoints.py",
                "│   ├── core/",
                "│   │   └── config.py",
                "│   ├── models/",
                "│   └── schemas/"
            ])
        # Frontend/JS project
        elif "TypeScript" in languages or "JavaScript" in languages:
            structure.extend([
                "├── package.json",
                "├── tsconfig.json",
                "├── src/",
                "│   ├── app/",
                "│   ├── components/",
                "│   ├── lib/",
                "│   └── types/"
            ])
        # Go project
        elif "Go" in languages:
            structure.extend([
                "├── go.mod",
                "├── go.sum",
                "├── main.go",
                "├── pkg/",
                "└── cmd/"
            ])
        # Default fallback
        else:
            structure.extend([
                "├── src/",
                "│   └── main.code",
                "├── config/",
                "└── scripts/"
            ])
            
        return "\n".join(structure)

    @staticmethod
    def _format_tree(tree_items: List[Dict[str, Any]]) -> str:
        """Formats GitHub tree items into a compact human-readable tree string."""
        paths = []
        for item in tree_items:
            path = item.get("path", "")
            # Skip noise directories
            if any(part in path.split("/") for part in ["node_modules", "venv", ".venv", ".git", ".next", "dist", "build", "__pycache__"]):
                continue
            paths.append(path)
            
        # Limit tree to top 40 paths for token optimization
        paths = sorted(paths)[:40]
        if not paths:
            return "No files detected."
            
        lines = []
        for p in paths:
            parts = p.split("/")
            indent = "    " * (len(parts) - 1)
            lines.append(f"{indent}├── {parts[-1]}")
            
        return "\n".join(lines)

    @classmethod
    async def preprocess_repository(
        cls,
        db: Any,
        repository: Repository,
        analysis: Optional[RepositoryAnalysis] = None,
    ) -> Dict[str, Any]:
        """Collects repository details, fetches readme + folder structure via GitHub,

        and builds a condensed data payload for LLM analysis.
        """
        repo_id = repository.id
        
        # 1. Fetch related data from DB
        # Languages
        lang_stmt = select(Language).where(Language.repository_id == repo_id)
        lang_res = await db.execute(lang_stmt)
        languages = [l.language_name for l in lang_res.scalars().all()]
        
        # Frameworks
        fw_stmt = select(Framework).where(Framework.repository_id == repo_id)
        fw_res = await db.execute(fw_stmt)
        frameworks = [f.framework_name for f in fw_res.scalars().all()]
        
        # Dependencies
        dep_stmt = select(Dependency).where(Dependency.repository_id == repo_id)
        dep_res = await db.execute(dep_stmt)
        dependencies = [f"{d.dependency_name} ({d.version})" for d in dep_res.scalars().all()]
        
        # Contributors / Commits count
        contrib_stmt = select(Contributor).where(Contributor.repository_id == repo_id)
        contrib_res = await db.execute(contrib_stmt)
        contributors = contrib_res.scalars().all()
        
        # Fetch analysis if not provided
        if not analysis:
            analysis_stmt = (
                select(RepositoryAnalysis)
                .where(RepositoryAnalysis.repository_id == repo_id)
                .order_by(RepositoryAnalysis.created_at.desc())
            )
            analysis_res = await db.execute(analysis_stmt)
            analysis = analysis_res.scalars().first()
            
        documentation_score = getattr(analysis, "documentation_score", 0) or 0
        complexity_score = getattr(analysis, "complexity_score", 0) or 0
        
        # 2. Get user token for GitHub API queries
        user_stmt = select(User).where(User.id == repository.user_id)
        user_res = await db.execute(user_stmt)
        user = user_res.scalars().first()
        access_token = user.access_token if user else None
        
        readme_content = ""
        folder_structure = ""
        
        headers = {}
        if access_token:
            headers["Authorization"] = f"token {access_token}"
            
        owner = repository.owner
        name = repository.name
        default_branch = repository.default_branch or "main"
        
        # 3. Fetch README from GitHub REST API
        if access_token:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    readme_url = f"{settings.github_api_url}/repos/{owner}/{name}/readme"
                    resp = await client.get(readme_url, headers=headers)
                    if resp.status_code == 200:
                        content_b64 = resp.json().get("content", "")
                        if content_b64:
                            readme_content = base64.b64decode(content_b64).decode("utf-8", errors="ignore")
            except Exception as e:
                logger.warning(f"Failed to fetch README from GitHub API: {e}")
                
        # Truncate README content to max 4000 characters for token optimization
        if readme_content:
            readme_content = readme_content[:4000]
        else:
            readme_content = repository.description or "No README documentation available."
            
        # 4. Fetch Folder Structure from GitHub REST API (recursive tree)
        if access_token:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    tree_url = f"{settings.github_api_url}/repos/{owner}/{name}/git/trees/{default_branch}?recursive=1"
                    resp = await client.get(tree_url, headers=headers)
                    if resp.status_code == 200:
                        tree_items = resp.json().get("tree", [])
                        folder_structure = cls._format_tree(tree_items)
            except Exception as e:
                logger.warning(f"Failed to fetch file tree from GitHub API: {e}")
                
        if not folder_structure:
            folder_structure = cls._build_mock_folder_structure(languages, frameworks, dependencies)
            
        # 5. Extract commit metadata stats
        total_commits = 0
        if analysis and analysis.commits_info:
            total_commits = analysis.commits_info.get("total_commits", 0)
            
        commit_statistics = {
            "total_commits": total_commits,
            "contributors_count": len(contributors),
        }
        
        return {
            "repository_name": name,
            "description": repository.description or "",
            "languages": languages,
            "frameworks": frameworks,
            "dependencies": dependencies,
            "readme": readme_content,
            "folder_structure": folder_structure,
            "commit_statistics": commit_statistics,
            "documentation_score": documentation_score,
            "complexity_score": complexity_score,
        }

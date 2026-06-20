from __future__ import annotations

import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.repository import Repository, Language
from app.services.github_service import fetch_repository_by_id, fetch_repository_languages

logger = logging.getLogger(__name__)


async def import_github_repository(
    db: AsyncSession,
    user_id: int,
    access_token: str,
    github_repo_id: int,
) -> Repository:
    """Import repository metadata and language breakdown from GitHub.

    If the repository has already been imported, this updates the existing metadata.
    """
    logger.info(f"Importing GitHub repository {github_repo_id} for user {user_id}")
    
    # 1. Fetch metadata from GitHub
    repo_data = await fetch_repository_by_id(access_token, github_repo_id)
    
    name = repo_data["name"]
    owner = repo_data["owner"]["login"]
    repo_url = repo_data.get("clone_url") or repo_data["html_url"]
    description = repo_data.get("description")
    stars = repo_data.get("stargazers_count", 0)
    forks = repo_data.get("forks_count", 0)
    watchers = repo_data.get("watchers_count", 0)
    default_branch = repo_data.get("default_branch", "main")
    primary_language = repo_data.get("language")

    # 2. Fetch language breakdown
    lang_data = await fetch_repository_languages(access_token, owner, name)
    total_bytes = sum(lang_data.values())
    languages_pct = []
    if total_bytes > 0:
        for lang_name, bytes_count in lang_data.items():
            pct = round((bytes_count / total_bytes) * 100, 2)
            languages_pct.append((lang_name, pct))
    elif primary_language:
        languages_pct.append((primary_language, 100.0))

    # 3. Check if repository already exists in our DB
    stmt = select(Repository).where(Repository.github_repo_id == github_repo_id)
    result = await db.execute(stmt)
    repo = result.scalars().first()

    if repo:
        # Update existing
        repo.user_id = user_id
        repo.name = name
        repo.owner = owner
        repo.repo_url = repo_url
        repo.description = description
        repo.stars = stars
        repo.forks = forks
        repo.watchers = watchers
        repo.default_branch = default_branch
        repo.language = primary_language
    else:
        # Create new
        repo = Repository(
            user_id=user_id,
            github_repo_id=github_repo_id,
            name=name,
            owner=owner,
            repo_url=repo_url,
            description=description,
            stars=stars,
            forks=forks,
            watchers=watchers,
            default_branch=default_branch,
            language=primary_language,
        )
        db.add(repo)
    
    # We must flush/commit to get the repository.id
    await db.flush()

    # Clear and update languages
    # Remove existing languages for this repo
    lang_delete_stmt = select(Language).where(Language.repository_id == repo.id)
    lang_result = await db.execute(lang_delete_stmt)
    for existing_lang in lang_result.scalars().all():
        await db.delete(existing_lang)

    # Insert new language percentages
    for lang_name, pct in languages_pct:
        lang_obj = Language(
            repository_id=repo.id,
            language_name=lang_name,
            percentage=pct,
        )
        db.add(lang_obj)

    await db.commit()
    await db.refresh(repo)
    
    logger.info(f"Successfully imported repository {repo.name} with ID {repo.id}")
    return repo

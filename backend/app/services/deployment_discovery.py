from __future__ import annotations

import base64
import logging
import re
from typing import Any
import httpx

from app.core.config import settings
from app.services.github_service import fetch_repository_by_id

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


def _auth_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "SkillLedger/0.1",
    }


async def discover_deployment_url(
    access_token: str,
    github_repo_id: int,
) -> dict[str, str | None]:
    """Attempts to discover the deployment URL of a repository from GitHub metadata

    and codebase README files using standard priority orders.
    """
    logger.info(f"Discovering deployment URL for github_repo_id={github_repo_id}")
    
    # 1. Fetch main repository metadata
    try:
        repo_data = await fetch_repository_by_id(access_token, github_repo_id)
    except Exception as e:
        logger.error(f"Failed to fetch repository by ID from GitHub: {e}")
        return {"deployment_url": None, "source": None}
        
    name = repo_data["name"]
    owner = repo_data["owner"]["login"]

    # ---- PRIORITY 1: GitHub Repository Homepage ----
    homepage = repo_data.get("homepage")
    if homepage:
        homepage = homepage.strip()
        if homepage.startswith(("http://", "https://")):
            logger.info(f"Discovered homepage URL in repository settings: {homepage}")
            return {"deployment_url": homepage, "source": "github_homepage"}

    # ---- PRIORITY 2: GitHub Pages Detection ----
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            pages_resp = await client.get(
                f"{settings.github_api_url}/repos/{owner}/{name}/pages",
                headers=_auth_headers(access_token),
            )
            if pages_resp.status_code == 200:
                pages_url = pages_resp.json().get("html_url")
                if pages_url:
                    pages_url = pages_url.strip()
                    logger.info(f"Discovered GitHub Pages URL: {pages_url}")
                    return {"deployment_url": pages_url, "source": "github_pages"}
    except Exception as e:
        logger.warning(f"Error querying GitHub Pages endpoint: {e}")

    # ---- PRIORITY 3: README Parsing ----
    readme_text = ""
    try:
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            readme_resp = await client.get(
                f"{settings.github_api_url}/repos/{owner}/{name}/readme",
                headers=_auth_headers(access_token),
            )
            if readme_resp.status_code == 200:
                content_b64 = readme_resp.json().get("content", "")
                if content_b64:
                    readme_text = base64.b64decode(content_b64).decode("utf-8", errors="ignore")
    except Exception as e:
        logger.warning(f"Error fetching README from GitHub API: {e}")

    if readme_text:
        # Define patterns for standard hosting providers
        patterns = [
            # Specific subdomains
            r"(https://[a-zA-Z0-9_\-]+\.vercel\.app)",
            r"(https://[a-zA-Z0-9_\-]+\.netlify\.app)",
            r"(https://[a-zA-Z0-9_\-]+\.onrender\.com)",
            r"(https://[a-zA-Z0-9_\-]+\.railway\.app)",
            # Custom domain matching associated with deployment keywords
            r"(?i)(?:live demo|demo|deployed at|live link|website|homepage)\s*[:\-]\s*(https?://[a-zA-Z0-9_\-\./]+)"
        ]
        
        for pat in patterns:
            match = re.search(pat, readme_text)
            if match:
                url = match.group(1).strip()
                # Clean trailing slashes/brackets if any
                url = url.rstrip("/)]}.")
                logger.info(f"Discovered deployment URL in README: {url}")
                return {"deployment_url": url, "source": "readme_parsing"}

    # ---- PRIORITY 4: GitHub Pages Fallback Construction ----
    # Best-effort construction of github pages url
    # e.g., if topics contains github-pages, we try standard structure
    topics = repo_data.get("topics", [])
    if "github-pages" in topics:
        fallback_url = f"https://{owner}.github.io/{name}"
        logger.info(f"Constructed fallback GitHub Pages URL: {fallback_url}")
        return {"deployment_url": fallback_url, "source": "github_pages_fallback"}

    # Check for other hosting-related topics, just to log them
    hosting_topics = {"vercel", "netlify", "render", "railway", "firebase-hosting"}
    detected_topics = hosting_topics.intersection(set(topics))
    if detected_topics:
        logger.info(f"Found hosting topics {list(detected_topics)} but no live URL could be extracted.")

    logger.info("No deployment URL could be automatically discovered.")
    return {"deployment_url": None, "source": None}

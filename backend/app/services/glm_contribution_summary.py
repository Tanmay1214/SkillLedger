from __future__ import annotations

import logging
import re
from typing import Any, Dict, List
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class GLMContributionSummary:
    """Service to generate recruiter-friendly contribution summaries using GLM-5.1 or standard heuristics."""

    @staticmethod
    def generate_heuristic_summary(
        primary_contributor: str,
        ownership_score: int,
        activity_score: int,
        modules: List[Dict[str, Any]],
        total_commits: int
    ) -> str:
        """Fallback to generate a clear recruiter explanation without API connections."""
        owned_mods = [m["module_name"] for m in modules if m["ownership_percentage"] > 40]
        if not owned_mods:
            owned_mods = [m["module_name"] for m in modules[:2]]
            
        mods_str = ", ".join(owned_mods) if owned_mods else "core components"
        
        return (
            f"{primary_contributor} appears to be the primary contributor to this repository, "
            f"demonstrating significant ownership of approximately {ownership_score}% across the codebase. "
            f"Key responsibilities include development of {mods_str}. "
            f"Commit analysis records {total_commits} commits with an active developer consistency score of {activity_score}/100, "
            f"evidencing high capability and authorship on this project."
        )

    @classmethod
    async def generate_contribution_summary(
        cls,
        primary_contributor: str,
        ownership_score: int,
        activity_score: int,
        modules: List[Dict[str, Any]],
        total_commits: int
    ) -> str:
        """Sends calculated git metrics to GLM API to generate a natural recruiter summary."""
        api_key = settings.glm_api_key
        
        # 1. Fallback to heuristic summary if no API key is set
        if not api_key:
            logger.info("No GLM_API_KEY configured. Falling back to heuristic summary generator.")
            return cls.generate_heuristic_summary(
                primary_contributor, ownership_score, activity_score, modules, total_commits
            )

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": "glm-4",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an expert recruiter and technical talent assessment officer. "
                        "Given git contribution analytics, write a brief, recruiter-friendly explanation "
                        "summarizing the developer's work, ownership percentage, and primary modules owned. "
                        "The summary MUST be professional, evidence-backed, and STRICTLY under 120 words. "
                        "Do not include any Markdown wrappers."
                    )
                },
                {
                    "role": "user",
                    "content": (
                        f"Developer: {primary_contributor}\n"
                        f"Code Ownership Score: {ownership_score}%\n"
                        f"Commit Activity Score: {activity_score}/100\n"
                        f"Total Commits: {total_commits}\n"
                        f"Module Ownerships: " + ", ".join([f"{m['module_name']} ({m['ownership_percentage']}%)" for m in modules]) + "\n"
                        f"Provide a brief recruiter-friendly summary."
                    )
                }
            ],
            "temperature": 0.3,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
                resp = await client.post(url, json=payload, headers=headers)
                
                if resp.status_code == 200:
                    content = resp.json()["choices"][0]["message"]["content"].strip()
                    # Clean markdown wrappers if any
                    clean_content = re.sub(r"```\s*|```", "", content).strip()
                    # Enforce the word limit strictly
                    words = clean_content.split()
                    if len(words) > 120:
                        clean_content = " ".join(words[:120]) + "..."
                    return clean_content
                else:
                    logger.error(f"GLM summary generation failed: {resp.status_code} - {resp.text}")
        except Exception as e:
            logger.error(f"GLM API summary generation connection error: {e}")

        # Final fallback
        return cls.generate_heuristic_summary(
            primary_contributor, ownership_score, activity_score, modules, total_commits
        )

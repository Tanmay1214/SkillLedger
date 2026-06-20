from __future__ import annotations

import logging
from typing import Dict, Any, List
from git import Repo

logger = logging.getLogger(__name__)


class ContributorAnalysisService:
    """Service to parse git repository commits and aggregate contribution metrics per developer."""

    @staticmethod
    def normalize_username(name: str, email: str) -> str:
        """Normalizes commit author name/email to a clean, lowercase username."""
        if email and "@" in email:
            # e.g., 'john.doe@gmail.com' -> 'john.doe'
            username = email.split("@")[0].lower()
            # Clean up common git private email structures
            if "+" in username:
                username = username.split("+")[-1]
            return username
            
        # Fallback to normalized name
        clean_name = "".join(c for c in name if c.isalnum() or c in ["-", "_", "."])
        return clean_name.lower() or "unknown-developer"

    @classmethod
    def analyze_contributors(cls, repo_path: str) -> Dict[str, Dict[str, Any]]:
        """Parses git commits and returns aggregated stats for all distinct contributors."""
        logger.info(f"Running Contributor Analysis on path: {repo_path}")
        stats: Dict[str, Dict[str, Any]] = {}
        
        try:
            repo = Repo(repo_path)
            commits = list(repo.iter_commits())
        except Exception as e:
            logger.error(f"Failed to read git repository for contributor analysis: {e}")
            return {}

        for commit in commits:
            author_name = commit.author.name or "Unknown"
            author_email = commit.author.email or ""
            
            username = cls.normalize_username(author_name, author_email)
            
            if username not in stats:
                stats[username] = {
                    "username": username,
                    "github_user_id": None,
                    "avatar_url": f"https://github.com/{username}.png",
                    "commits": 0,
                    "additions": 0,
                    "deletions": 0,
                    "files_modified_counts": {},  # file_path -> count of commits touching it
                    "file_insertions": {},       # file_path -> lines added
                    "file_deletions": {},        # file_path -> lines deleted
                }
                
            stats[username]["commits"] += 1
            
            try:
                # Retrieve files changed, insertions, and deletions in this commit
                commit_stats = commit.stats
                for filepath, file_delta in commit_stats.files.items():
                    # Accumulate line numbers
                    ins = file_delta.get("insertions", 0)
                    dels = file_delta.get("deletions", 0)
                    
                    stats[username]["additions"] += ins
                    stats[username]["deletions"] += dels
                    
                    # Accumulate file-specific modifications
                    stats[username]["files_modified_counts"][filepath] = stats[username]["files_modified_counts"].get(filepath, 0) + 1
                    stats[username]["file_insertions"][filepath] = stats[username]["file_insertions"].get(filepath, 0) + ins
                    stats[username]["file_deletions"][filepath] = stats[username]["file_deletions"].get(filepath, 0) + dels
            except Exception as e:
                # Catch exceptions on root commits or binary diff failures
                logger.debug(f"Skipped commit stats parsing for {commit.hexsha}: {e}")
                
        return stats

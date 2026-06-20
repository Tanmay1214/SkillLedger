from __future__ import annotations

import logging
from datetime import datetime, date
from typing import Dict, Any, List
from git import Repo

logger = logging.getLogger(__name__)


class CommitAnalysisService:
    """Service to execute deep analysis on git commits, timelines, and developer activity metrics."""

    @staticmethod
    def analyze_commit_history(repo_path: str) -> Dict[str, Any]:
        """Iterates over git commits to calculate timeline, frequency, active days, and averages."""
        logger.info(f"Running Commit History Analysis on path: {repo_path}")
        try:
            repo = Repo(repo_path)
            commits = list(repo.iter_commits())
        except Exception as e:
            logger.error(f"Failed to load git repository commit history: {e}")
            return {
                "total_commits": 0,
                "active_days": 0,
                "weekly_average": 0,
                "duration_days": 1,
                "timeline": {}
            }

        total_commits = len(commits)
        if total_commits == 0:
            return {
                "total_commits": 0,
                "active_days": 0,
                "weekly_average": 0,
                "duration_days": 1,
                "timeline": {}
            }

        # Retrieve commit dates
        dates: List[date] = []
        timeline: Dict[str, int] = {}
        
        for commit in commits:
            # commit.committed_date is epoch seconds
            dt = datetime.fromtimestamp(commit.committed_date)
            d = dt.date()
            dates.append(d)
            
            d_str = d.strftime("%Y-%m-%d")
            timeline[d_str] = timeline.get(d_str, 0) + 1

        # Calculate durations
        first_date = min(dates)
        last_date = max(dates)
        duration_days = max(1, (last_date - first_date).days)
        
        # Calculate active days (unique days with commits)
        active_days = len(set(dates))
        
        # Calculate weekly average (weeks = duration / 7, minimum 1 week)
        weeks = max(1.0, duration_days / 7.0)
        weekly_average = int(round(total_commits / weeks))

        return {
            "total_commits": total_commits,
            "active_days": active_days,
            "weekly_average": weekly_average,
            "duration_days": duration_days,
            "timeline": timeline,  # Dict of YYYY-MM-DD -> Commit Count
        }

from __future__ import annotations

import logging
from typing import Dict, Any, List, Set, Tuple

logger = logging.getLogger(__name__)


class OwnershipEngine:
    """Calculates file-level and module-level code ownership, developer activity metrics, and contribution scores."""

    @staticmethod
    def classify_file_module(filepath: str) -> str:
        """Determines the logical module classification of a file based on its pathname."""
        f_lower = filepath.lower()
        if any(kw in f_lower for kw in ["auth", "login", "signup", "jwt", "token", "session", "permission", "credentials"]):
            return "Authentication"
        if any(kw in f_lower for kw in ["db", "database", "models", "schema", "migrate", "alembic", "sql", "postgres", "sqlite", "query"]):
            return "Database Layer"
        if any(kw in f_lower for kw in ["api", "routes", "endpoints", "controllers", "views", "router", "http", "request"]):
            return "API Services"
        if any(kw in f_lower for kw in ["frontend", "src/app", "src/components", "public", "styles", "css", "html", "js", "ts", "jsx", "tsx", "assets", "pages"]):
            return "Frontend"
        if any(kw in f_lower for kw in ["deploy", "docker", "kubernetes", "ci", "cd", "github/workflows", "nginx", "pm2", "jenkins", "kubernetes"]):
            return "Deployment"
        return "Core"

    @classmethod
    def calculate_ownership(
        cls,
        contributor_data: Dict[str, Dict[str, Any]],
        commit_history_stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculates final file, module, activity, and code ownership scores across all contributors."""
        logger.info("Executing Ownership calculation calculations...")
        
        # 1. Collate all modified files
        all_files: Set[str] = set()
        for c_stats in contributor_data.values():
            all_files.update(c_stats["files_modified_counts"].keys())
            
        total_files = len(all_files)
        
        # 2. Determine file ownership: who modified each file most frequently
        file_owners: Dict[str, str] = {}  # filepath -> username
        files_owned_count: Dict[str, int] = {uname: 0 for uname in contributor_data.keys()}
        
        for filepath in all_files:
            max_mods = -1
            owner = ""
            for uname, c_stats in contributor_data.items():
                mods = c_stats["files_modified_counts"].get(filepath, 0)
                if mods > max_mods:
                    max_mods = mods
                    owner = uname
                elif mods == max_mods and max_mods > 0:
                    # Tie-breaker: who has more insertions
                    ins_current = c_stats["file_insertions"].get(filepath, 0)
                    ins_best = contributor_data[owner]["file_insertions"].get(filepath, 0)
                    if ins_current > ins_best:
                        owner = uname
            if owner and max_mods > 0:
                file_owners[filepath] = owner
                files_owned_count[owner] += 1

        # 3. Classify files into modules and compute module ownership
        modules_files: Dict[str, List[str]] = {}  # module -> list of file paths
        for filepath in all_files:
            module = cls.classify_file_module(filepath)
            if module not in modules_files:
                modules_files[module] = []
            modules_files[module].append(filepath)

        # Calculate module ownership percentage per user
        # module_ownership[module_name][username] = percentage (fraction of files owned in this module)
        module_ownerships: Dict[str, Dict[str, float]] = {}
        for mod, files_list in modules_files.items():
            module_ownerships[mod] = {}
            mod_total_files = len(files_list)
            for uname in contributor_data.keys():
                owned_in_mod = sum(1 for f in files_list if file_owners.get(f) == uname)
                pct = (owned_in_mod / mod_total_files) * 100.0 if mod_total_files > 0 else 0.0
                module_ownerships[mod][uname] = round(pct, 2)

        # 4. Total aggregates across all developers for share calculations
        total_commits = sum(c["commits"] for c in contributor_data.values())
        total_additions = sum(c["additions"] for c in contributor_data.values())
        total_deletions = sum(c["deletions"] for c in contributor_data.values())

        # 5. Calculate scores per developer
        processed_contributors = []
        for uname, c_stats in contributor_data.items():
            commit_share = (c_stats["commits"] / total_commits) * 100.0 if total_commits > 0 else 0.0
            additions_share = (c_stats["additions"] / total_additions) * 100.0 if total_additions > 0 else commit_share
            deletions_share = (c_stats["deletions"] / total_deletions) * 100.0 if total_deletions > 0 else commit_share
            file_share = (files_owned_count[uname] / total_files) * 100.0 if total_files > 0 else commit_share
            
            # Module ownership share = average of ownership percentages across all active modules
            mod_shares = [module_ownerships[m][uname] for m in modules_files.keys()]
            module_share = sum(mod_shares) / len(mod_shares) if mod_shares else 0.0

            # Weighted Formula: 35% Commits, 25% Additions, 15% Deletions, 15% Files, 10% Modules
            ownership_score = (
                (commit_share * 0.35) +
                (additions_share * 0.25) +
                (deletions_share * 0.15) +
                (file_share * 0.15) +
                (module_share * 0.10)
            )
            ownership_score = max(0, min(100, int(round(ownership_score))))

            # Activity score calculations per developer
            # Since git logs don't directly record active days per user inside contributor_data, we approximate:
            # active days: number of unique files modified, or proportional commit rate
            active_days_approx = min(commit_history_stats.get("active_days", 1), max(1, int(c_stats["commits"] * 0.7)))
            weekly_avg_approx = max(1, int(c_stats["commits"] / max(1.0, commit_history_stats.get("duration_days", 7) / 7.0)))
            activity_score = min(98, int((active_days_approx * 5) + (weekly_avg_approx * 2) + min(20, commit_history_stats.get("duration_days", 7))))

            processed_contributors.append({
                "username": uname,
                "github_user_id": c_stats["github_user_id"],
                "avatar_url": c_stats["avatar_url"],
                "total_commits": c_stats["commits"],
                "lines_added": c_stats["additions"],
                "lines_deleted": c_stats["deletions"],
                "ownership_percentage": round(commit_share, 2),  # Raw commit share for DB list compatibility
                "ownership_score": ownership_score,               # Weighted overall score
                "activity_score": activity_score,
            })

        # 6. Detect Primary Contributor
        primary_uname = "unknown"
        max_score = -1
        primary_activity = 0
        for pc in processed_contributors:
            if pc["ownership_score"] > max_score:
                max_score = pc["ownership_score"]
                primary_uname = pc["username"]
                primary_activity = pc["activity_score"]
                
        # 7. Confidence Score (Report level)
        # High commit ownership, module ownership, and file ownership increase confidence
        confidence = 50
        if max_score > 0:
            primary_file_share = (files_owned_count.get(primary_uname, 0) / total_files) * 100.0 if total_files > 0 else 50.0
            confidence = min(99, int(round((max_score * 0.6) + (primary_file_share * 0.3) + 10)))
            confidence = max(20, confidence)

        # 8. Modules report list
        # List modules and the primary owner's percentage
        modules_report = []
        for mod, shares in module_ownerships.items():
            modules_report.append({
                "module_name": mod,
                "ownership_percentage": int(round(shares.get(primary_uname, 0.0)))
            })

        return {
            "primary_contributor": primary_uname,
            "ownership_score": max(1, max_score),
            "activity_score": max(1, primary_activity),
            "confidence": confidence,
            "modules": modules_report,
            "contributors": processed_contributors,
            "module_ownerships_grid": module_ownerships,  # Raw grid data for backend queries
        }

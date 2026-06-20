from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.deps import OAUTH_STATE_COOKIE
from app.models.repository import Repository, Contributor, ContributionReport, ModuleOwnership
from app.schemas.user import GithubProfile
from app.services.commit_analysis_service import CommitAnalysisService
from app.services.contributor_analysis_service import ContributorAnalysisService
from app.services.ownership_engine import OwnershipEngine
from app.services.glm_contribution_summary import GLMContributionSummary
from app.services.contribution_verification_service import ContributionVerificationService

GITHUB_PROFILE_PAYLOAD = {
    "id": 99,
    "login": "flowuser",
    "name": "Flow User",
    "email": "flow@example.com",
    "avatar_url": "https://avatars.githubusercontent.com/u/99",
    "html_url": "https://github.com/flowuser",
}


@pytest.fixture
async def authenticated_client(client):
    """Logs in a user and returns the authenticated client."""
    login_resp = await client.get("/api/v1/auth/github/login")
    state = login_resp.json()["state"]
    
    with patch(
        "app.api.auth_routes.github_service.exchange_code_for_token",
        new=AsyncMock(return_value="gho_fake_token"),
    ), patch(
        "app.api.auth_routes.github_service.fetch_profile",
        new=AsyncMock(return_value=GithubProfile(**GITHUB_PROFILE_PAYLOAD)),
    ):
        await client.get(
            "/api/v1/auth/github/callback",
            params={"code": "fake_code", "state": state},
            cookies={OAUTH_STATE_COOKIE: state},
        )
    return client


def test_normalize_username():
    """Verifies that email prefixes and generic name characters are cleaned correctly."""
    assert ContributorAnalysisService.normalize_username("Tanmay Shrivastava", "tanmay@example.com") == "tanmay"
    assert ContributorAnalysisService.normalize_username("A B", "a+b@github.com") == "b"
    assert ContributorAnalysisService.normalize_username("User-Name!", "") == "user-name"


def test_classify_file_module():
    """Verifies classifying code paths into modules."""
    assert OwnershipEngine.classify_file_module("backend/app/auth/routes.py") == "Authentication"
    assert OwnershipEngine.classify_file_module("alembic/versions/001_init.py") == "Database Layer"
    assert OwnershipEngine.classify_file_module("frontend/src/app/page.tsx") == "Frontend"
    assert OwnershipEngine.classify_file_module("docker-compose.yml") == "Deployment"
    assert OwnershipEngine.classify_file_module("backend/app/services/analytics.py") == "Core"


def test_ownership_and_activity_scoring():
    """Verifies math scoring logic for weighted ownership, confidence, and activity scores."""
    # Seed mock contributor data
    contributor_data = {
        "tanmay": {
            "username": "tanmay",
            "github_user_id": None,
            "avatar_url": "url",
            "commits": 80,
            "additions": 1000,
            "deletions": 200,
            "files_modified_counts": {"app/main.py": 10, "app/auth.py": 5},
            "file_insertions": {"app/main.py": 600, "app/auth.py": 400},
            "file_deletions": {"app/main.py": 150, "app/auth.py": 50},
        },
        "collaborator": {
            "username": "collaborator",
            "github_user_id": None,
            "avatar_url": "url",
            "commits": 20,
            "additions": 200,
            "deletions": 50,
            "files_modified_counts": {"app/main.py": 2},
            "file_insertions": {"app/main.py": 200},
            "file_deletions": {"app/main.py": 50},
        }
    }
    
    commit_history_stats = {
        "total_commits": 100,
        "active_days": 10,
        "duration_days": 30,
        "weekly_average": 23,
    }
    
    res = OwnershipEngine.calculate_ownership(contributor_data, commit_history_stats)
    
    assert res["primary_contributor"] == "tanmay"
    # tanmay has 80% commits, >80% additions/deletions, and owns both files (main.py and auth.py)
    assert res["ownership_score"] > 70
    assert res["confidence"] > 50
    assert len(res["modules"]) > 0
    
    # Check that collaborator has lower ownership score
    collab_stats = next(c for c in res["contributors"] if c["username"] == "collaborator")
    assert collab_stats["ownership_score"] < 40


def test_glm_summary_generation_fallback():
    """Verifies that heuristic summary fallback produces a high-quality explanation."""
    summary = GLMContributionSummary.generate_heuristic_summary(
        primary_contributor="tanmay",
        ownership_score=78,
        activity_score=86,
        modules=[{"module_name": "Authentication", "ownership_percentage": 90}],
        total_commits=145
    )
    assert "tanmay" in summary
    assert "78%" in summary
    assert "Authentication" in summary
    assert "145" in summary


@pytest.mark.asyncio
async def test_contribution_apis_integration(authenticated_client, db_session):
    """Creates a mock repository, runs analysis, triggers contribution analysis, and checks GET APIs."""
    # 1. Insert mock repository & completed analysis
    repo = Repository(
        user_id=1,  # matches authenticated_client user
        github_repo_id=98765,
        name="contrib-repo",
        owner="flowuser",
        repo_url="https://github.com/flowuser/contrib-repo",
        description="Demo repo for contributions",
        stars=10,
        forks=2,
        watchers=2,
        default_branch="main",
        language="Python",
    )
    db_session.add(repo)
    await db_session.commit()
    await db_session.refresh(repo)

    # 2. Test POST trigger analyze Contributions
    # Mock verify_and_save_contributions so background task doesn't execute git clone/AI
    with patch(
        "app.services.contribution_verification_service.ContributionVerificationService.verify_and_save_contributions",
        new=AsyncMock(return_value=ContributionReport(
            repository_id=repo.id,
            primary_contributor="flowuser",
            ownership_score=85,
            activity_score=90,
            contribution_summary="Recruiter summary here."
        ))
    ):
        resp = await authenticated_client.post(f"/api/v1/contributions/analyze/{repo.id}")
        assert resp.status_code == 202
        assert resp.json()["status"] == "processing"

    # 3. Insert mock report, contributor, and module ownership records manually to test GET APIs
    report = ContributionReport(
        repository_id=repo.id,
        primary_contributor="flowuser",
        ownership_score=85,
        activity_score=90,
        contribution_summary="Recruiter summary here."
    )
    db_session.add(report)
    
    contrib = Contributor(
        repository_id=repo.id,
        username="flowuser",
        commits=45,
        additions=800,
        deletions=200,
        ownership_percentage=85.0,
        activity_score=90,
        avatar_url="https://github.com/flowuser.png"
    )
    db_session.add(contrib)
    
    module_own = ModuleOwnership(
        repository_id=repo.id,
        username="flowuser",
        module_name="Authentication",
        ownership_percentage=90.0
    )
    db_session.add(module_own)
    await db_session.commit()

    # 4. Fetch contribution report GET endpoint
    report_resp = await authenticated_client.get(f"/api/v1/contributions/{repo.id}")
    assert report_resp.status_code == 200
    report_data = report_resp.json()
    assert report_data["primary_contributor"] == "flowuser"
    assert report_data["ownership_score"] == 85
    assert report_data["activity_score"] == 90
    assert report_data["summary"] == "Recruiter summary here."
    assert len(report_data["modules"]) == 1
    assert report_data["modules"][0]["module"] == "Authentication"
    assert report_data["modules"][0]["ownership"] == 90

    # 5. Fetch contributors list GET endpoint
    contribs_resp = await authenticated_client.get(f"/api/v1/contributions/{repo.id}/contributors")
    assert contribs_resp.status_code == 200
    contribs_list = contribs_resp.json()
    assert len(contribs_list) == 1
    assert contribs_list[0]["username"] == "flowuser"
    assert contribs_list[0]["total_commits"] == 45
    assert contribs_list[0]["avatar_url"] == "https://github.com/flowuser.png"

    # 6. Fetch ownership breakdown GET endpoint
    own_resp = await authenticated_client.get(f"/api/v1/contributions/{repo.id}/ownership")
    assert own_resp.status_code == 200
    own_list = own_resp.json()
    assert len(own_list) == 1
    assert own_list[0]["username"] == "flowuser"
    assert own_list[0]["module_name"] == "Authentication"
    assert own_list[0]["ownership_percentage"] == 90.0

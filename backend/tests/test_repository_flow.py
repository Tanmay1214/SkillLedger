from __future__ import annotations

import os
import tempfile
import shutil
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.deps import OAUTH_STATE_COOKIE
from app.models.repository import Repository, RepositoryAnalysis, Language, Framework, Dependency, Contributor
from app.services.analysis_service import run_analysis_pipeline

GITHUB_PROFILE_PAYLOAD = {
    "id": 99,
    "login": "flowuser",
    "name": "Flow User",
    "email": "flow@example.com",
    "avatar_url": "https://avatars.githubusercontent.com/u/99",
    "html_url": "https://github.com/flowuser",
}

MOCK_GITHUB_REPOS = [
    {
        "id": 12345,
        "name": "test-repo",
        "owner": {"login": "flowuser"},
        "private": False,
        "language": "Python",
        "stargazers_count": 42,
        "forks_count": 5,
        "watchers_count": 42,
        "default_branch": "main",
        "clone_url": "https://github.com/flowuser/test-repo.git",
        "description": "A wonderful test repository"
    }
]


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
        new=AsyncMock(return_value=__import__("app.schemas.user", fromlist=["GithubProfile"]).GithubProfile(
            **GITHUB_PROFILE_PAYLOAD
        )),
    ):
        await client.get(
            "/api/v1/auth/github/callback",
            params={"code": "fake_code", "state": state},
            cookies={OAUTH_STATE_COOKIE: state},
        )
    return client


@pytest.mark.asyncio
async def test_get_github_repositories(authenticated_client):
    with patch(
        "app.api.repository_routes.fetch_user_repositories",
        new=AsyncMock(return_value=MOCK_GITHUB_REPOS),
    ):
        resp = await authenticated_client.get("/api/v1/repositories/github")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["repositories"]) == 1
        repo = data["repositories"][0]
        assert repo["github_id"] == 12345
        assert repo["name"] == "test-repo"
        assert repo["owner"] == "flowuser"
        assert repo["private"] is False
        assert repo["language"] == "Python"
        assert repo["stars"] == 42


@pytest.mark.asyncio
async def test_import_and_analysis_flow(authenticated_client, db_session):
    # Mocking GitHub service calls inside the import service
    with patch(
        "app.services.github_import_service.fetch_repository_by_id",
        new=AsyncMock(return_value=MOCK_GITHUB_REPOS[0]),
    ), patch(
        "app.services.github_import_service.fetch_repository_languages",
        new=AsyncMock(return_value={"Python": 9000, "HTML": 1000}),
    ), patch(
        "app.api.repository_routes.run_analysis_pipeline"
    ) as mock_pipeline:
        
        # 1. Post to import endpoint
        resp = await authenticated_client.post(
            "/api/v1/repositories/import",
            json={"github_repo_id": 12345}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "queued"
        repo_id = data["repository_id"]
        assert repo_id is not None
        
        # Verify background task was scheduled
        mock_pipeline.assert_called_once()
        
        # 2. Get list of imported repositories
        list_resp = await authenticated_client.get("/api/v1/repositories")
        assert list_resp.status_code == 200
        repos = list_resp.json()
        assert len(repos) == 1
        assert repos[0]["id"] == repo_id
        assert repos[0]["name"] == "test-repo"
        
        # 3. Get repository detail by ID
        detail_resp = await authenticated_client.get(f"/api/v1/repositories/{repo_id}")
        assert detail_resp.status_code == 200
        assert detail_resp.json()["name"] == "test-repo"
        
        # 4. Get analysis report (should show status=queued since background task is mocked)
        analysis_resp = await authenticated_client.get(f"/api/v1/repositories/{repo_id}/analysis")
        assert analysis_resp.status_code == 200
        analysis = analysis_resp.json()
        assert analysis["analysis_status"] == "queued"
        assert len(analysis["languages"]) == 2
        # Sort by percentage
        languages = sorted(analysis["languages"], key=lambda l: l["percentage"], reverse=True)
        assert languages[0]["language_name"] == "Python"
        assert languages[0]["percentage"] == 90.0
        assert languages[1]["language_name"] == "HTML"
        assert languages[1]["percentage"] == 10.0


@pytest.mark.asyncio
async def test_analysis_pipeline_execution(authenticated_client, db_session):
    # Set up a fake repository in a temp directory with standard manifest files
    fake_repo_dir = tempfile.mkdtemp()
    
    try:
        # Create a package.json
        with open(os.path.join(fake_repo_dir, "package.json"), "w", encoding="utf-8") as f:
            f.write('{"dependencies": {"react": "^18.2.0", "tailwindcss": "^3.0.0"}}')
            
        # Create a requirements.txt
        with open(os.path.join(fake_repo_dir, "requirements.txt"), "w", encoding="utf-8") as f:
            f.write("fastapi==0.100.0\npytest>=7.0.0\n")
            
        # Create a python file with security finding (hardcoded secret and unsafe eval)
        with open(os.path.join(fake_repo_dir, "app.py"), "w", encoding="utf-8") as f:
            f.write(
                'API_KEY = "dummy-secret-value-longer-than-16-chars"\n'
                'def run_code(user_input):\n'
                '    eval(user_input)\n'
            )
            
        # Create a README.md
        with open(os.path.join(fake_repo_dir, "README.md"), "w", encoding="utf-8") as f:
            f.write(
                "# Test Repo\n\n"
                "## Installation\n"
                "Run pip install -r requirements.txt\n\n"
                "## Usage\n"
                "Run uvicorn app.main:app\n"
            )

        # 1. Create Repository and RepositoryAnalysis records manually in db
        repo = Repository(
            user_id=1, # matches the logged-in user id in pytest environment
            github_repo_id=99999,
            name="fake-analyzed-repo",
            owner="flowuser",
            repo_url="https://github.com/flowuser/fake-analyzed-repo.git",
            stars=10,
            default_branch="main"
        )
        db_session.add(repo)
        await db_session.flush()
        
        analysis = RepositoryAnalysis(
            repository_id=repo.id,
            analysis_status="queued"
        )
        db_session.add(analysis)
        await db_session.commit()
        
        # 2. Run the analysis pipeline directly, mocking the clone step to return our fake directory
        # and patching the session factory to use the same engine as the test database
        from sqlalchemy.ext.asyncio import async_sessionmaker
        test_session_factory = async_sessionmaker(bind=db_session.bind, expire_on_commit=False)
        
        with patch(
            "app.services.analysis_service.clone_repository",
            return_value=fake_repo_dir
        ), patch(
            "app.services.analysis_service.cleanup_repository"
        ), patch(
            "app.services.analysis_service.async_session_factory",
            new=test_session_factory
        ):
            await run_analysis_pipeline(
                repository_id=repo.id,
                analysis_id=analysis.id,
                repo_url=repo.repo_url,
                access_token="gho_fake"
            )
            
        # 3. Refresh and fetch analysis from database to verify results
        await db_session.refresh(analysis)
        assert analysis.analysis_status == "completed"
        assert analysis.complexity_score is not None
        assert analysis.security_score is not None
        assert analysis.documentation_score == 60 # readme + install + usage (20*3)
        
        # Verify findings
        assert len(analysis.findings) == 2
        titles = [f["title"] for f in analysis.findings]
        assert "Hardcoded Secret / API Key" in titles
        assert "Usage of eval/exec" in titles
        
        # Verify frameworks and dependencies
        from sqlalchemy import select
        fw_stmt = select(Framework).where(Framework.repository_id == repo.id)
        fw_res = await db_session.execute(fw_stmt)
        frameworks = [f.framework_name for f in fw_res.scalars().all()]
        assert "FastAPI" in frameworks
        assert "React" in frameworks
        assert "Tailwind CSS" in frameworks
        
        dep_stmt = select(Dependency).where(Dependency.repository_id == repo.id)
        dep_res = await db_session.execute(dep_stmt)
        deps = {d.dependency_name: d.version for d in dep_res.scalars().all()}
        assert "fastapi" in deps
        assert "react" in deps
        
    finally:
        shutil.rmtree(fake_repo_dir, ignore_errors=True)

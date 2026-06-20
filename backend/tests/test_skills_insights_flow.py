from __future__ import annotations

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.deps import OAUTH_STATE_COOKIE
from app.models.repository import Repository, RepositoryAnalysis, Skill, ProjectInsight
from app.schemas.user import GithubProfile
from app.services.skill_preprocessor import SkillExtractionPreprocessor
from app.services.glm_prompt_builder import GLMPromptBuilder
from app.services.glm_client import GLMClient
from app.services.skill_extraction_service import SkillExtractionService

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


def test_glm_prompt_builder():
    """Verifies prompt building format constraints and schemas."""
    data = {
        "repository_name": "TestRepo",
        "description": "Short description",
        "languages": ["Python", "JavaScript"],
        "frameworks": ["FastAPI", "React"],
        "dependencies": ["sqlalchemy==2.0.36"],
        "commit_statistics": {"total_commits": 42},
        "documentation_score": 80,
        "complexity_score": 35,
        "folder_structure": "├── main.py",
        "readme": "Sample Readme Content"
    }
    
    sys_prompt = GLMPromptBuilder.build_system_prompt()
    user_prompt = GLMPromptBuilder.build_user_prompt(data)
    
    assert "Principal Software Architect" in sys_prompt
    assert "project_type" in sys_prompt
    assert "skills" in sys_prompt
    assert "TestRepo" in user_prompt
    assert "sqlalchemy" in user_prompt


@pytest.mark.asyncio
async def test_preprocessor_fallback_structure():
    """Verifies that preprocessor constructs a mock tree if API fails or is unavailable."""
    languages = ["Python"]
    frameworks = ["FastAPI"]
    dependencies = ["uvicorn"]
    
    tree = SkillExtractionPreprocessor._build_mock_folder_structure(languages, frameworks, dependencies)
    assert "requirements.txt" in tree
    assert "app/" in tree
    assert "main.py" in tree
    
    # Test for frontend languages
    tree_fe = SkillExtractionPreprocessor._build_mock_folder_structure(["TypeScript"], ["React"], [])
    assert "package.json" in tree_fe
    assert "tsconfig.json" in tree_fe


@pytest.mark.asyncio
async def test_glm_client_api_request():
    """Tests the GLMClient connection response parsing and error retries."""
    client = GLMClient("fake_api_key")
    
    # 1. Success case
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"project_type": "API Service", "project_category": ["Backend Development"], "complexity_level": "Intermediate", "skills": [], "project_summary": "Summary", "technical_summary": "Tech"}'
                }
            }
        ]
    }
    
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_resp)):
        res = await client.extract_project_metadata("sys", "user")
        assert res is not None
        assert res["project_type"] == "API Service"
        assert res["complexity_level"] == "Intermediate"

    # 2. Rate limit fallback case (should retry and eventually return None if all fail)
    mock_resp_429 = MagicMock()
    mock_resp_429.status_code = 429
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_resp_429)):
        res = await client.extract_project_metadata("sys", "user")
        assert res is None


@pytest.mark.asyncio
async def test_heuristic_fallback_extraction():
    """Verifies that heuristic skill extraction produces high-confidence metrics without LLM access."""
    data = {
        "repository_name": "TestRepo",
        "description": "Short description",
        "languages": ["Python"],
        "frameworks": ["FastAPI"],
        "dependencies": ["psycopg2 (2.9.10)", "boto3 (1.30.0)"],
        "commit_statistics": {"total_commits": 25},
        "documentation_score": 85,
        "complexity_score": 35,
        "folder_structure": "├── main.py",
        "readme": "Sample Readme"
    }
    
    extracted = SkillExtractionService._run_heuristic_extraction(data)
    assert extracted["project_type"] == "API Service"
    assert "Backend Development" in extracted["project_category"]
    assert extracted["complexity_level"] == "Intermediate"
    
    skills = {s["name"]: s for s in extracted["skills"]}
    assert "Python" in skills
    assert "FastAPI" in skills
    assert "REST API Development" in skills
    assert "Version Control (Git)" in skills
    assert "Technical Writing" in skills


@pytest.mark.asyncio
async def test_skills_insights_apis_integration(authenticated_client, db_session):
    """Creates a mock repository, runs analysis, triggers skills extraction, and checks REST endpoints."""
    # 1. Insert mock repository & completed analysis
    repo = Repository(
        user_id=1,  # matches authenticated_client user
        github_repo_id=98765,
        name="ai-insights-repo",
        owner="flowuser",
        repo_url="https://github.com/flowuser/ai-insights-repo",
        description="Demo repo for LLM testing",
        stars=10,
        forks=2,
        watchers=2,
        default_branch="main",
        language="Python",
    )
    db_session.add(repo)
    await db_session.commit()
    await db_session.refresh(repo)
    
    from app.models.repository import Framework, Language
    db_session.add(Framework(repository_id=repo.id, framework_name="FastAPI"))
    db_session.add(Language(repository_id=repo.id, language_name="Python", percentage=100.0))
    await db_session.commit()
    
    analysis = RepositoryAnalysis(
        repository_id=repo.id,
        complexity_score=40,
        security_score=95,
        documentation_score=75,
        analysis_status="completed",
        metrics={"total_loc": 250},
        findings=[],
        commits_info={"total_commits": 18},
        doc_report={"readme_filename": "README.md", "checklist": {}}
    )
    db_session.add(analysis)
    await db_session.commit()

    # 2. Test extraction API triggers processing
    # Patch extract_and_save_skills so the background task doesn't hit Zhipu AI
    with patch(
        "app.services.skill_extraction_service.SkillExtractionService.extract_and_save_skills",
        new=AsyncMock(return_value=ProjectInsight(
            repository_id=repo.id,
            project_type="API Service",
            project_category=["Backend Development"],
            project_summary="A backend API project.",
            technical_summary="Built using Python.",
            complexity_level="Intermediate",
        ))
    ):
        resp = await authenticated_client.post(f"/api/v1/skills/extract/{repo.id}")
        assert resp.status_code == 202
        assert resp.json()["status"] == "processing"

    # 3. Trigger manual extraction synchronously to test DB writes and GET APIs
    # This triggers the heuristic pipeline because settings.glm_api_key is None
    insight = await SkillExtractionService.extract_and_save_skills(db_session, repo.id)
    assert insight is not None
    assert insight.project_type == "API Service"
    
    # 4. Fetch skills GET endpoint
    skills_resp = await authenticated_client.get(f"/api/v1/skills/{repo.id}")
    assert skills_resp.status_code == 200
    skills_list = skills_resp.json()
    assert len(skills_list) > 0
    assert any(s["skill_name"] == "Python" for s in skills_list)

    # 5. Fetch project insights GET endpoint
    insight_resp = await authenticated_client.get(f"/api/v1/insights/{repo.id}")
    assert insight_resp.status_code == 200
    insight_data = insight_resp.json()
    assert insight_data["project_type"] == "API Service"
    assert "Backend Development" in insight_data["project_category"]
    assert "complexity_level" in insight_data

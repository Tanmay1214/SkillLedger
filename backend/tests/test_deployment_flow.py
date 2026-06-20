from __future__ import annotations

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bs4 import BeautifulSoup

from app.api.deps import OAUTH_STATE_COOKIE
from app.models.repository import Repository, DeploymentReport, Framework
from app.services.deployment_discovery import discover_deployment_url
from app.services.deployment_verification import (
    run_deployment_verification,
    check_ssl,
    score_security_headers,
    validate_page_content,
)

GITHUB_PROFILE_PAYLOAD = {
    "id": 99,
    "login": "flowuser",
    "name": "Flow User",
    "email": "flow@example.com",
    "avatar_url": "https://avatars.githubusercontent.com/u/99",
    "html_url": "https://github.com/flowuser",
}

MOCK_GITHUB_REPO_METADATA = {
    "id": 12345,
    "name": "test-repo",
    "owner": {"login": "flowuser"},
    "homepage": "https://proofforge.vercel.app",
    "description": "A test repository description",
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
async def test_ssl_checker_valid():
    # Mocking socket and ssl context wrap
    mock_socket = MagicMock()
    mock_ssock = MagicMock()
    mock_ssock.getpeercert.return_value = {
        "notAfter": "May 17 23:59:59 2028 GMT" # 2028 is long in the future
    }
    
    with patch("socket.create_connection", return_value=mock_socket), \
         patch("ssl.create_default_context") as mock_ctx:
        
        mock_ctx.return_value.wrap_socket.return_value.__enter__.return_value = mock_ssock
        
        res = check_ssl("valid-ssl-domain.com")
        assert res["ssl_enabled"] is True
        assert res["certificate_valid"] is True
        assert res["expires_in_days"] > 0


@pytest.mark.asyncio
async def test_ssl_checker_invalid():
    with patch("socket.create_connection", side_effect=Exception("Connection timed out")):
        res = check_ssl("broken-ssl-domain.com")
        assert res["ssl_enabled"] is False
        assert res["certificate_valid"] is False
        assert res["expires_in_days"] is None


def test_security_headers_scorer():
    headers = {
        "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
        "Content-Security-Policy": "default-src 'self'",
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff"
    }
    res = score_security_headers(headers)
    assert res["security_headers_score"] == 70 # 20+20+15+15
    assert "Referrer-Policy" in res["missing_headers"]
    assert "Permissions-Policy" in res["missing_headers"]


def test_validate_page_content_placeholders():
    html_placeholder = "<html><head><title>Under Construction</title></head><body>Welcome to Vercel! Deploy your app.</body></html>"
    res = validate_page_content(html_placeholder)
    assert res["homepage_valid"] is False
    assert res["title_found"] is True
    assert res["is_placeholder"] is True

    html_valid = "<html><head><title>My SaaS Dashboard</title><meta name='description' content='A SaaS dashboard'></head><body>Welcome to the dashboard page content!</body></html>"
    res2 = validate_page_content(html_valid)
    assert res2["homepage_valid"] is True
    assert res2["title_found"] is True
    assert res2["title"] == "My SaaS Dashboard"


@pytest.mark.asyncio
async def test_discovery_service_flow():
    # Test Priority 1: Repository settings homepage
    with patch(
        "app.services.deployment_discovery.fetch_repository_by_id",
        new=AsyncMock(return_value=MOCK_GITHUB_REPO_METADATA),
    ):
        res = await discover_deployment_url("gho_fake", 12345)
        assert res["deployment_url"] == "https://proofforge.vercel.app"
        assert res["source"] == "github_homepage"

    # Test Priority 2: Pages Endpoint (if homepage is missing)
    repo_no_homepage = MOCK_GITHUB_REPO_METADATA.copy()
    repo_no_homepage["homepage"] = None
    
    with patch(
        "app.services.deployment_discovery.fetch_repository_by_id",
        new=AsyncMock(return_value=repo_no_homepage),
    ), patch(
        "httpx.AsyncClient.get"
    ) as mock_get:
        
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"html_url": "https://flowuser.github.io/test-repo"}
        mock_get.return_value = mock_resp
        
        res = await discover_deployment_url("gho_fake", 12345)
        assert res["deployment_url"] == "https://flowuser.github.io/test-repo"
        assert res["source"] == "github_pages"


@pytest.mark.asyncio
async def test_deployment_apis_integration(authenticated_client, db_session):
    # 1. Create a Repository model manually in db
    repo = Repository(
        user_id=1, # matches the logged-in user id in pytest environment
        github_repo_id=12345,
        name="test-repo",
        owner="flowuser",
        repo_url="https://github.com/flowuser/test-repo.git",
        stars=10,
        default_branch="main"
    )
    db_session.add(repo)
    await db_session.flush()
    
    # 2. Test Discovery Endpoint
    # Mock GitHub details API
    with patch(
        "app.api.deployment_routes.discover_deployment_url",
        new=AsyncMock(return_value={"deployment_url": "https://proofforge.vercel.app", "source": "github_homepage"}),
    ):
        resp = await authenticated_client.post(f"/api/v1/deployments/discover/{repo.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["deployment_url"] == "https://proofforge.vercel.app"
        assert data["source"] == "github_homepage"
        
        # Verify repository homepage column was updated in db
        await db_session.refresh(repo)
        assert repo.homepage == "https://proofforge.vercel.app"

    # 3. Test Verification Endpoint
    # We will mock the deployment verification checks to avoid actual HTTP calls
    mock_html = """
    <html>
      <head>
        <title>SaaS Dashboard App</title>
        <link rel="stylesheet" href="/style.css">
        <script src="/script.js"></script>
      </head>
      <body>
        <h1>App Live Demo</h1>
        <a href="/dashboard">Internal Dashboard Route</a>
      </body>
    </html>
    """
    
    # Mocking HTTPX client responses inside deployment_verification
    async def mock_httpx_get(url_arg, **kwargs):
        resp = MagicMock()
        url_str = str(url_arg)
        if url_str == "https://proofforge.vercel.app":
            resp.status_code = 200
            resp.headers = {
                "Server": "Vercel",
                "Strict-Transport-Security": "max-age=63072000",
                "Content-Security-Policy": "default-src 'self'"
            }
            resp.text = mock_html
        elif "/style.css" in url_str or "/script.js" in url_str or "/dashboard" in url_str:
            resp.status_code = 200
            resp.text = "ok"
        else:
            resp.status_code = 404
        return resp

    async def mock_httpx_head(url_arg, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        return resp

    # Mocking SSL check
    mock_ssl_data = {
        "ssl_enabled": True,
        "certificate_valid": True,
        "expires_in_days": 80
    }
    
    # Mocking patch session factory inside run_deployment_verification
    from sqlalchemy.ext.asyncio import async_sessionmaker
    test_session_factory = async_sessionmaker(bind=db_session.bind, expire_on_commit=False)

    with patch("httpx.AsyncClient.get", side_effect=mock_httpx_get), \
         patch("httpx.AsyncClient.head", side_effect=mock_httpx_head), \
         patch("app.services.deployment_verification.check_ssl", return_value=mock_ssl_data), \
         patch("app.services.deployment_verification.async_session_factory", new=test_session_factory):
             
        resp = await authenticated_client.post(f"/api/v1/deployments/verify/{repo.id}")
        assert resp.status_code == 200
        data = resp.json()
        
        # Verify scores and providers
        assert data["provider"] == "Vercel"
        assert data["reachable"] is True
        assert data["ssl_enabled"] is True
        assert data["status_code"] == 200
        assert data["deployment_score"] > 50

        # Verify DB Report creation
        from sqlalchemy import select
        stmt = select(DeploymentReport).where(DeploymentReport.repository_id == repo.id)
        res = await db_session.execute(stmt)
        report = res.scalars().first()
        assert report is not None
        assert report.deployment_score == data["deployment_score"]
        assert report.provider == "Vercel"
        
    # 4. Test Report Retrieval Endpoint
    report_resp = await authenticated_client.get(f"/api/v1/deployments/report/{repo.id}")
    assert report_resp.status_code == 200
    report_data = report_resp.json()
    assert report_data["id"] == report.id
    assert report_data["deployment_score"] == report.deployment_score

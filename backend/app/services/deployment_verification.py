from __future__ import annotations

import logging
import re
import socket
import ssl
from datetime import datetime
from urllib.parse import urljoin, urlparse
import httpx
from bs4 import BeautifulSoup

from app.core.config import settings
from sqlalchemy import select
from app.database.session import async_session_factory
from app.models.repository import Repository, DeploymentReport, Framework

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = httpx.Timeout(5.0, connect=3.0)


def check_ssl(hostname: str) -> dict:
    """Verifies HTTPS is enabled, tests the certificate, and calculates expiration days."""
    if not hostname:
        return {"ssl_enabled": False, "certificate_valid": False, "expires_in_days": None}
        
    context = ssl.create_default_context()
    try:
        # Attempt SSL socket handshake on port 443
        with socket.create_connection((hostname, 443), timeout=5.0) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                if not cert:
                    return {"ssl_enabled": True, "certificate_valid": False, "expires_in_days": None}
                
                # Parse certificate expiry date (e.g. 'notAfter': 'May 17 23:59:59 2026 GMT')
                not_after_str = cert.get("notAfter")
                if not not_after_str:
                    return {"ssl_enabled": True, "certificate_valid": False, "expires_in_days": None}
                
                not_after = datetime.strptime(not_after_str, "%b %d %H:%M:%S %Y %Z")
                delta = not_after - datetime.utcnow()
                days_left = max(0, delta.days)
                return {
                    "ssl_enabled": True,
                    "certificate_valid": True,
                    "expires_in_days": days_left,
                }
    except Exception as e:
        logger.warning(f"SSL validation check failed for {hostname}: {e}")
        return {"ssl_enabled": False, "certificate_valid": False, "expires_in_days": None}


def score_security_headers(headers: dict[str, str]) -> dict:
    """Calculates a score (out of 100) based on presence of key security headers."""
    score = 0
    missing = []
    
    # Case-insensitive headers check
    normalized = {k.lower(): v for k, v in headers.items()}
    
    # HSTS
    if "strict-transport-security" in normalized:
        score += 20
    else:
        missing.append("Strict-Transport-Security")
        
    # CSP
    if "content-security-policy" in normalized:
        score += 20
    else:
        missing.append("Content-Security-Policy")
        
    # X-Frame-Options
    if "x-frame-options" in normalized:
        score += 15
    else:
        missing.append("X-Frame-Options")
        
    # X-Content-Type-Options
    if "x-content-type-options" in normalized:
        score += 15
    else:
        missing.append("X-Content-Type-Options")
        
    # Referrer-Policy
    if "referrer-policy" in normalized:
        score += 15
    else:
        missing.append("Referrer-Policy")
        
    # Permissions-Policy
    if "permissions-policy" in normalized:
        score += 15
    else:
        missing.append("Permissions-Policy")
        
    return {
        "security_headers_score": score,
        "missing_headers": missing,
    }


def validate_page_content(html: str) -> dict:
    """Verifies the page title, meta description, and checks for generic hosting placeholders."""
    if not html:
        return {"homepage_valid": False, "title_found": False, "meta_description_found": False}
        
    soup = BeautifulSoup(html, "html.parser")
    
    # Title Check
    title_tag = soup.find("title")
    title_text = title_tag.text.strip() if title_tag else ""
    
    # Meta Description Check
    meta_tag = soup.find("meta", attrs={"name": "description"})
    meta_desc = meta_tag.get("content", "").strip() if meta_tag else ""
    
    # Generic Placeholder/Default text detection
    html_lower = html.lower()
    placeholders = [
        "welcome to vercel",
        "deploy your app",
        "coming soon",
        "under construction",
        "default page",
        "welcome to nginx",
        "apache2 ubuntu default page",
        "site not found",
        "no deployment found",
        "welcome to your new app",
    ]
    is_placeholder = any(p in html_lower for p in placeholders)
    
    # Obvious error text detection
    errors = ["404 not found", "500 internal server error", "error 404", "error 500"]
    has_error_text = any(err in html_lower for err in errors)
    
    homepage_valid = (not is_placeholder) and (not has_error_text) and len(html.strip()) > 100
    
    return {
        "homepage_valid": homepage_valid,
        "title_found": bool(title_text),
        "meta_description_found": bool(meta_desc),
        "title": title_text,
        "is_placeholder": is_placeholder,
    }


async def check_asset_health(soup: BeautifulSoup, base_url: str) -> dict:
    """Extracts stylesheet links, script sources, and images, and checks if they resolve."""
    assets = []
    
    # 1. Stylesheets
    for link in soup.find_all("link", rel="stylesheet"):
        href = link.get("href")
        if href:
            assets.append(urljoin(base_url, href))
            
    # 2. Scripts
    for script in soup.find_all("script", src=True):
        src = script.get("src")
        if src:
            assets.append(urljoin(base_url, src))
            
    # 3. Images
    for img in soup.find_all("img", src=True):
        src = img.get("src")
        if src:
            assets.append(urljoin(base_url, src))
            
    # Sample up to 10 assets
    sampled = list(set(assets))[:10]
    if not sampled:
        return {"asset_health_score": 100}
        
    reachable = 0
    async with httpx.AsyncClient(timeout=3.0) as client:
        for asset in sampled:
            try:
                # Use HEAD request for speed, fallback to GET if HEAD fails (e.g. 405 Method Not Allowed)
                resp = await client.head(asset, follow_redirects=True)
                if resp.status_code in [200, 304]:
                    reachable += 1
                else:
                    resp_get = await client.get(asset, follow_redirects=True)
                    if resp_get.status_code in [200, 304]:
                        reachable += 1
            except Exception:
                pass
                
    score = int((reachable / len(sampled)) * 100)
    return {"asset_health_score": score}


async def check_internal_links(soup: BeautifulSoup, base_url: str) -> dict:
    """Extracts internal links on the page and tests them for broken routes."""
    links = []
    parsed_base = urlparse(base_url)
    base_domain = parsed_base.netloc
    
    for a in soup.find_all("a", href=True):
        href = a.get("href")
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
            
        full_url = urljoin(base_url, href)
        parsed_url = urlparse(full_url)
        # Only verify internal links
        if parsed_url.netloc == base_domain:
            links.append(full_url)
            
    # Sample up to 20 links
    sampled = list(set(links))[:20]
    if not sampled:
        return {"broken_links": 0, "internal_link_score": 100}
        
    broken_count = 0
    async with httpx.AsyncClient(timeout=3.0) as client:
        for link in sampled:
            try:
                resp = await client.get(link, follow_redirects=True)
                if resp.status_code >= 400:
                    broken_count += 1
            except Exception:
                broken_count += 1
                
    score = int(((len(sampled) - broken_count) / len(sampled)) * 100)
    return {
        "broken_links": broken_count,
        "internal_link_score": score,
    }


def detect_hosting_provider(headers: dict[str, str], hostname: str) -> str:
    """Inspects HTTP headers and DNS domain suffix patterns to detect the hosting provider."""
    normalized = {k.lower(): v for k, v in headers.items()}
    server = normalized.get("server", "").lower()
    
    if "vercel" in server or "x-vercel-id" in normalized:
        return "Vercel"
    if "netlify" in server or "x-nf-request-id" in normalized:
        return "Netlify"
    if "render" in server or "x-render-request-id" in normalized:
        return "Render"
    if "github.com" in server or hostname.endswith(".github.io"):
        return "GitHub Pages"
    if "firebase" in server or "x-firebase-id" in normalized:
        return "Firebase Hosting"
    if "railway" in server or "x-railway-id" in normalized:
        return "Railway"
        
    return "Custom Server"


async def check_deployment_ai_consistency(
    repo_summary: str,
    tech_detected: str,
    html_summary: str,
    deployment_url: str,
) -> dict:
    """Uses Gemini API to cross-verify if the live deployment webpage

    matches the repository details. If no API key is set, falls back to
    a keyword-based heuristic matcher.
    """
    api_key = settings.gemini_api_key
    if not api_key:
        logger.info("No GEMINI_API_KEY found. Falling back to keyword-based heuristic verification.")
        # Fallback comparison based on overlapping words
        repo_words = set(re.findall(r"\w+", f"{repo_summary} {tech_detected}".lower()))
        html_words = set(re.findall(r"\w+", html_summary.lower()))
        overlap = repo_words.intersection(html_words)
        
        matches = True
        confidence = 70
        if len(repo_words) > 0 and len(overlap) == 0:
            matches = False
            confidence = 50
            
        return {
            "deployment_matches_repository": matches,
            "confidence": confidence,
        }
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    prompt = f"""
Analyze the live deployed webpage text snippet and determine if it is consistent with the repository codebase description and tech stack.

Repository description: {repo_summary}
Detected frameworks/libraries: {tech_detected}
Deployment URL: {deployment_url}

Deployed webpage text snippet:
{html_summary}

Provide your output in strict JSON format matching this schema:
{{
  "deployment_matches_repository": boolean,
  "confidence": number (between 0 and 100)
}}
"""
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(
                url,
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"responseMimeType": "application/json"},
                },
            )
            if resp.status_code == 200:
                import json
                result_text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                # Clean prompt formatting (```json ... ```) if any
                clean_text = re.sub(r"```(?:json)?\s*|```", "", result_text).strip()
                data = json.loads(clean_text)
                return {
                    "deployment_matches_repository": bool(data.get("deployment_matches_repository", True)),
                    "confidence": int(data.get("confidence", 75)),
                }
    except Exception as e:
        logger.error(f"Failed calling Gemini API: {e}")
        
    return {"deployment_matches_repository": True, "confidence": 75}


async def run_deployment_verification(
    repository_id: int,
    deployment_url: str,
) -> DeploymentReport:
    """Performs full Deployment Verification against the URL and returns a report.

    Automatically saves it in the database under `deployment_reports`.
    """
    logger.info(f"Running deployment verification for repository_id={repository_id} on URL: {deployment_url}")
    
    # 1. Reachability Check
    reachable = False
    status_code = None
    response_time = 0.0
    headers = {}
    html_content = ""
    
    parsed_url = urlparse(deployment_url)
    hostname = parsed_url.hostname or ""
    
    start_time = datetime.utcnow()
    try:
        # Resolve DNS
        socket.gethostbyname(hostname)
        
        async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
            resp = await client.get(deployment_url, follow_redirects=True)
            status_code = resp.status_code
            headers = dict(resp.headers)
            html_content = resp.text
            
            # Reachable if status code is not in server/client errors
            reachable = status_code < 400
    except Exception as e:
        logger.warning(f"Reachability check failed: {e}")
        
    end_time = datetime.utcnow()
    response_time = (end_time - start_time).total_seconds() * 1000.0  # ms
    
    # 2. SSL check
    ssl_data = check_ssl(hostname)
    
    # 3. Security headers check
    headers_data = score_security_headers(headers)
    
    # 4. Basic page validation
    page_data = validate_page_content(html_content)
    
    # 5. Asset health check
    soup = BeautifulSoup(html_content, "html.parser")
    asset_data = await check_asset_health(soup, deployment_url)
    
    # 6. Internal link validation
    link_data = await check_internal_links(soup, deployment_url)
    
    # 7. Hosting provider detection
    provider = detect_hosting_provider(headers, hostname)
    
    # 8. Fetch repository tech stack from DB for AI comparison
    repo_summary = ""
    tech_detected = ""
    async with async_session_factory() as db:
        repo_stmt = select(Repository).where(Repository.id == repository_id)
        repo_res = await db.execute(repo_stmt)
        repo = repo_res.scalars().first()
        if repo:
            repo_summary = repo.description or repo.name
            
            # Fetch frameworks
            fw_stmt = select(Framework).where(Framework.repository_id == repository_id)
            fw_res = await db.execute(fw_stmt)
            tech_detected = ", ".join([f.framework_name for f in fw_res.scalars().all()])

    # Extract HTML title/meta for AI validation text snippet
    html_summary = f"Title: {page_data.get('title', '')}\nContent snippet: {html_content[:500]}"
    
    # Run AI Validation
    ai_data = await check_deployment_ai_consistency(
        repo_summary=repo_summary,
        tech_detected=tech_detected,
        html_summary=html_summary,
        deployment_url=deployment_url,
    )
    
    # 9. Calculate Overall Score
    # 25% Reachability, 20% SSL, 20% Security Headers, 15% Asset Health, 10% Link Validation, 10% AI
    reachability_contrib = 25 if (reachable and status_code == 200) else (10 if reachable else 0)
    ssl_contrib = 20 if (ssl_data["ssl_enabled"] and ssl_data["certificate_valid"]) else (5 if ssl_data["ssl_enabled"] else 0)
    headers_contrib = int(headers_data["security_headers_score"] * 0.20)
    asset_contrib = int(asset_data["asset_health_score"] * 0.15)
    link_contrib = int(link_data["internal_link_score"] * 0.10)
    
    ai_score = 100 if ai_data["deployment_matches_repository"] else max(20, 100 - (100 - ai_data["confidence"]))
    ai_contrib = int(ai_score * 0.10)
    
    overall_score = reachability_contrib + ssl_contrib + headers_contrib + asset_contrib + link_contrib + ai_contrib
    
    # Limit score boundaries
    overall_score = max(0, min(100, overall_score))
    
    # 10. Persist report in database
    async with async_session_factory() as db:
        # Create ORM object
        report = DeploymentReport(
            repository_id=repository_id,
            deployment_url=deployment_url,
            provider=provider,
            reachable=reachable,
            status_code=status_code,
            response_time=response_time,
            ssl_enabled=ssl_data["ssl_enabled"],
            ssl_expiry_days=ssl_data["expires_in_days"],
            security_headers_score=headers_data["security_headers_score"],
            asset_health_score=asset_data["asset_health_score"],
            internal_link_score=link_data["internal_link_score"],
            deployment_score=overall_score,
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)
        
        logger.info(f"Deployment verification report saved. ID={report.id}, Score={overall_score}")
        return report

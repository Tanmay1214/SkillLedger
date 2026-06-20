from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class DeploymentDiscoverResponse(BaseModel):
    """Response of POST /deployments/discover/{repository_id}."""

    deployment_url: Optional[str] = None
    source: Optional[str] = None


class DeploymentReportResponse(BaseModel):
    """Response of GET /deployments/report/{repository_id} or POST /deployments/verify/{repository_id}."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    repository_id: int
    deployment_url: str
    provider: Optional[str] = None
    reachable: bool
    status_code: Optional[int] = None
    response_time: Optional[float] = None
    ssl_enabled: bool
    ssl_expiry_days: Optional[int] = None
    security_headers_score: int
    asset_health_score: int
    internal_link_score: int
    deployment_score: int
    created_at: datetime

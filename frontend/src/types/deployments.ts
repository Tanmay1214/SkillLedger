/**
 * Deployment types mirroring backend deployment schemas.
 */

export interface DeploymentDiscoverResponse {
  deployment_url: string | null;
  source: string | null;
}

export interface DeploymentReportResponse {
  id: number;
  repository_id: number;
  deployment_url: string;
  provider: string | null;
  reachable: boolean;
  status_code: number | null;
  response_time: number | null;
  ssl_enabled: boolean;
  ssl_expiry_days: number | null;
  security_headers_score: number;
  asset_health_score: number;
  internal_link_score: number;
  deployment_score: number;
  created_at: string;
}

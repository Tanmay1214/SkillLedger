/**
 * TypeScript types for the Contribution Verification Engine.
 */

export interface Contributor {
  id: number;
  repository_id: number;
  github_user_id: number | null;
  username: string;
  avatar_url: string | null;
  total_commits: number;
  lines_added: number;
  lines_deleted: number;
  ownership_percentage: number;
  activity_score: number;
  created_at: string | null;
}

export interface ModuleOwnership {
  id: number;
  repository_id: number;
  username: string;
  module_name: string;
  ownership_percentage: number;
}

export interface ModuleReportItem {
  module: string;
  ownership: number;
}

export interface ContributionReport {
  primary_contributor: string;
  ownership_score: number;
  activity_score: number;
  confidence: number;
  modules: ModuleReportItem[];
  summary: string;
}

export interface ContributionProcessResponse {
  status: string;
}

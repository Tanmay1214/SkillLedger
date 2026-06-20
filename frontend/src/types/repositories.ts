/**
 * Repository and static analysis types mirroring backend schemas.
 */

export interface GithubRepoPublic {
  github_id: number;
  name: string;
  owner: string;
  private: boolean;
  language: string | null;
  stars: number;
}

export interface GithubRepoListResponse {
  repositories: GithubRepoPublic[];
}

export interface RepositoryImportRequest {
  github_repo_id: number;
}

export interface RepositoryImportResponse {
  repository_id: number;
  status: string;
}

export interface RepositoryPublic {
  id: number;
  github_repo_id: number;
  name: string;
  owner: string;
  repo_url: string;
  description: string | null;
  stars: number;
  forks: number;
  watchers: number;
  default_branch: string;
  language: string | null;
  homepage: string | null;
  created_at: string;
  updated_at: string;
}

export interface LanguageResponse {
  language_name: string;
  percentage: number;
}

export interface FrameworkResponse {
  framework_name: string;
}

export interface DependencyResponse {
  dependency_name: string;
  version: string;
}

export interface ContributorResponse {
  github_user_id: number | null;
  username: string;
  commits: number;
  additions: number;
  deletions: number;
  ownership_percentage: number;
}

export interface ComplexFunction {
  file: string;
  function: string;
  complexity: number;
  loc: number;
  parameter_count: number;
}

export interface ComplexityMetrics {
  total_loc: number;
  average_complexity: number;
  max_complexity: number;
  function_count: number;
  complex_functions: ComplexFunction[];
}

export interface SecurityFinding {
  file: string;
  line: number;
  severity: "high" | "medium" | "low";
  title: string;
  description: string;
}

export interface DocumentationReport {
  readme_filename: string;
  checklist: {
    readme_exists: boolean;
    installation_instructions: boolean;
    usage_guide: boolean;
    features_list: boolean;
    contribution_guidelines: boolean;
  };
  length: number;
}

export interface CommitMetric {
  sha: string;
  author: string;
  date: string | null;
  message: string;
}

export interface CommitsMetrics {
  total_commits: number;
  commits: CommitMetric[];
}

export interface RepositoryAnalysisReport {
  repository: RepositoryPublic;
  languages: LanguageResponse[];
  frameworks: FrameworkResponse[];
  dependencies: DependencyResponse[];
  contributors: ContributorResponse[];
  complexity_score: number | null;
  security_score: number | null;
  documentation_score: number | null;
  analysis_status: string; // "queued" | "cloning" | "analyzing" | "completed" | "failed"
  complexity_metrics: ComplexityMetrics | null;
  security_findings: SecurityFinding[] | null;
  documentation_report: DocumentationReport | null;
  commits_metrics: CommitsMetrics | null;
}

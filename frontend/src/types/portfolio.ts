// TypeScript types for the Portfolio Generator API

export interface PortfolioSkill {
  skill_name: string;
  category: string;
  confidence_score: number;
}

export interface SkillGroup {
  category: string;
  skills: PortfolioSkill[];
}

export interface PortfolioProject {
  id: number;
  name: string;
  description: string | null;
  repo_url: string;
  language: string | null;
  stars: number;
  forks: number;
  // Scores
  build_score: number | null;
  proof_score: number | null;
  complexity_score: number | null;
  security_score: number | null;
  documentation_score: number | null;
  // Contribution
  contribution_percentage: number | null;
  contribution_summary: string | null;
  primary_contributor: string | null;
  // Deployment
  deployment_url: string | null;
  deployment_reachable: boolean | null;
  deployment_score: number | null;
  provider: string | null;
  // Insights
  project_type: string | null;
  complexity_level: string | null;
  project_summary: string | null;
  technical_summary: string | null;
  project_categories: string[];
  // Skills
  skills: PortfolioSkill[];
  frameworks: string[];
}

export interface PortfolioHeader {
  username: string;
  name: string | null;
  avatar_url: string | null;
  github_url: string;
  repositories_verified: number;
  avg_build_score: number;
  avg_proof_score: number;
}

export interface VerificationSummary {
  repositories_analyzed: number;
  deployments_verified: number;
  verified_skills_count: number;
  primary_contributor_projects: number;
}

export interface PortfolioResponse {
  header: PortfolioHeader;
  verification_summary: VerificationSummary;
  skill_groups: SkillGroup[];
  projects: PortfolioProject[];
}

/**
 * Typed API client for the SkillLedger backend.
 *
 * Notes:
 *  - `credentials: "include"` so the httpOnly session cookie is sent on every
 *    request (CORS `allowCredentials: true` on the backend honors this).
 *  - We never read or store tokens in JS; the backend owns the cookies.
 *  - Errors are normalized into `ApiError` for predictable UI handling.
 */
import { API_URL } from "@/lib/config";
import type {
  ApiErrorResponse,
  AuthUrlResponse,
  CallbackSuccess,
  User,
} from "@/types/auth";
import type {
  GithubRepoListResponse,
  RepositoryImportResponse,
  RepositoryPublic,
  RepositoryAnalysisReport,
} from "@/types/repositories";
import type {
  DeploymentDiscoverResponse,
  DeploymentReportResponse,
} from "@/types/deployments";
import type {
  Skill,
  ProjectInsight,
  SkillExtractionResponse,
} from "@/types/skills_insights";
import type {
  Contributor,
  ModuleOwnership,
  ContributionReport,
  ContributionProcessResponse,
} from "@/types/contributions";
import type { PortfolioResponse, PortfolioProject, SkillGroup } from "@/types/portfolio";

export class ApiError extends Error {
  readonly status: number;
  readonly errorCode: string | null;

  constructor(message: string, status: number, errorCode: string | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.errorCode = errorCode;
  }
}

async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init.headers ?? {}),
    },
  });

  if (!res.ok) {
    let detail = `Request failed with status ${res.status}`;
    let errorCode: string | null = null;
    try {
      const body = (await res.json()) as ApiErrorResponse;
      detail = body.detail ?? detail;
      errorCode = body.error_code ?? null;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(detail, res.status, errorCode);
  }

  // 204 / empty bodies
  if (res.status === 204) {
    return undefined as T;
  }
  const text = await res.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

export const apiClient = {
  /** `GET /auth/github/login` — returns the GitHub authorize URL. */
  getLoginUrl: () => request<AuthUrlResponse>("/auth/github/login"),

  /** `GET /auth/me` — returns the authenticated user (401 if not logged in). */
  getMe: () => request<User>("/auth/me"),

  /** `POST /auth/logout` — clears the session cookies server-side. */
  logout: () =>
    request<{ message: string }>("/auth/logout", { method: "POST" }),

  /** `POST /auth/refresh` — rotate the token pair (manual refresh). */
  refresh: () => request<{ message: string }>("/auth/refresh", { method: "POST" }),

  /** `GET /repositories/github` — fetch all user repositories from GitHub. */
  getGithubRepos: () => request<GithubRepoListResponse>("/repositories/github"),

  /** `POST /repositories/import` — import a GitHub repository. */
  importRepository: (githubRepoId: number) =>
    request<RepositoryImportResponse>("/repositories/import", {
      method: "POST",
      body: JSON.stringify({ github_repo_id: githubRepoId }),
    }),

  /** `GET /repositories` — list all imported repositories. */
  getImportedRepositories: () => request<RepositoryPublic[]>("/repositories"),

  /** `GET /repositories/{id}` — fetch a single repository's metadata. */
  getRepository: (id: number) => request<RepositoryPublic>(`/repositories/${id}`),

  /** `GET /repositories/{id}/analysis` — retrieve the compiled analysis report. */
  getRepositoryAnalysis: (id: number) =>
    request<RepositoryAnalysisReport>(`/repositories/${id}/analysis`),

  /** `POST /deployments/discover/{repository_id}` — automatically discover deployment URL. */
  discoverDeployment: (repositoryId: number) =>
    request<DeploymentDiscoverResponse>(`/deployments/discover/${repositoryId}`, { method: "POST" }),

  /** `POST /deployments/verify/{repository_id}` — run deployment verification scan. */
  verifyDeployment: (repositoryId: number, url?: string) => {
    const query = url ? `?url=${encodeURIComponent(url)}` : "";
    return request<DeploymentReportResponse>(`/deployments/verify/${repositoryId}${query}`, { method: "POST" });
  },

  /** `GET /deployments/report/{repository_id}` — fetch the latest deployment report. */
  getDeploymentReport: (repositoryId: number) =>
    request<DeploymentReportResponse>(`/deployments/report/${repositoryId}`),

  /** `POST /skills/extract/{repository_id}` — trigger skills extraction process. */
  extractSkills: (repositoryId: number) =>
    request<SkillExtractionResponse>(`/skills/extract/${repositoryId}`, { method: "POST" }),

  /** `GET /skills/{repository_id}` — fetch extracted skills. */
  getSkills: (repositoryId: number) =>
    request<Skill[]>(`/skills/${repositoryId}`),

  /** `GET /insights/{repository_id}` — fetch project recruiter insights. */
  getProjectInsights: (repositoryId: number) =>
    request<ProjectInsight>(`/insights/${repositoryId}`),

  /** `POST /contributions/analyze/{repository_id}` — run contribution analysis. */
  analyzeContributions: (repositoryId: number) =>
    request<ContributionProcessResponse>(`/contributions/analyze/${repositoryId}`, { method: "POST" }),

  /** `GET /contributions/{repository_id}` — retrieve contribution report. */
  getContributionReport: (repositoryId: number) =>
    request<ContributionReport>(`/contributions/${repositoryId}`),

  /** `GET /contributions/{repository_id}/contributors` — retrieve all repository contributors. */
  getContributors: (repositoryId: number) =>
    request<Contributor[]>(`/contributions/${repositoryId}/contributors`),

  /** `GET /contributions/{repository_id}/ownership` — retrieve module ownership breakdown. */
  getOwnershipBreakdown: (repositoryId: number) =>
    request<ModuleOwnership[]>(`/contributions/${repositoryId}/ownership`),

  // ── Portfolio ──────────────────────────────────────────────────────────────

  /** `GET /portfolio/{username}` — full portfolio for a given GitHub user. */
  getPortfolio: (username: string) =>
    request<PortfolioResponse>(`/portfolio/${username}`),

  /** `GET /portfolio/{username}/projects` — list of projects for a user. */
  getPortfolioProjects: (username: string) =>
    request<PortfolioProject[]>(`/portfolio/${username}/projects`),

  /** `GET /portfolio/{username}/skills` — aggregated skill groups for a user. */
  getPortfolioSkills: (username: string) =>
    request<SkillGroup[]>(`/portfolio/${username}/skills`),
};

export type { CallbackSuccess };



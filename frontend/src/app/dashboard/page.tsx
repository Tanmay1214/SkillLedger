"use client";

import { useRouter, useSearchParams } from "next/navigation";
import type { Route } from "next";
import { Suspense, useEffect, useState, useMemo, useCallback } from "react";
import { 
  GitBranch, 
  Github, 
  Star, 
  Shield, 
  FileText, 
  Activity, 
  RefreshCw, 
  Search, 
  Download, 
  AlertTriangle, 
  CheckCircle, 
  Eye,
  Settings,
  AlertCircle
} from "lucide-react";

import { ProtectedRoute } from "@/components/auth/protected-route";
import { UserProfileCard } from "@/components/auth/user-profile-card";
import { useAuth } from "@/context/auth-context";
import { Spinner } from "@/components/ui/spinner";
import { apiClient, ApiError } from "@/lib/api-client";
import type { RepositoryPublic, GithubRepoPublic } from "@/types/repositories";

function DashboardContent() {
  const { user, refreshUser } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const justLoggedIn = searchParams.get("login") === "success";

  // State variables
  const [activeTab, setActiveTab] = useState<"imported" | "github">("imported");
  const [importedRepos, setImportedRepos] = useState<RepositoryPublic[]>([]);
  const [githubRepos, setGithubRepos] = useState<GithubRepoPublic[]>([]);
  const [analysisStatuses, setAnalysisStatuses] = useState<Record<number, string>>({});
  const [analysisScores, setAnalysisScores] = useState<Record<number, { complexity: number | null, security: number | null, documentation: number | null }>>({});
  const [loadingImported, setLoadingImported] = useState(true);
  const [loadingGithub, setLoadingGithub] = useState(false);
  const [githubError, setGithubError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [importingRepoId, setImportingRepoId] = useState<number | null>(null);

  // Re-fetch me after OAuth success login
  useEffect(() => {
    if (justLoggedIn) {
      void refreshUser();
    }
  }, [justLoggedIn, refreshUser]);

  // 1. Fetch imported repositories on mount
  const fetchImportedRepositories = async (silent = false) => {
    if (!silent) setLoadingImported(true);
    try {
      const repos = await apiClient.getImportedRepositories();
      setImportedRepos(repos);
      
      // Fetch analysis status for each repo
      const statusMap: Record<number, string> = {};
      const scoreMap: Record<number, { complexity: number | null, security: number | null, documentation: number | null }> = {};
      
      await Promise.all(
        repos.map(async (repo) => {
          try {
            const report = await apiClient.getRepositoryAnalysis(repo.id);
            statusMap[repo.id] = report.analysis_status;
            scoreMap[repo.id] = {
              complexity: report.complexity_score,
              security: report.security_score,
              documentation: report.documentation_score
            };
          } catch {
            statusMap[repo.id] = "not_started";
            scoreMap[repo.id] = { complexity: null, security: null, documentation: null };
          }
        })
      );
      
      setAnalysisStatuses(statusMap);
      setAnalysisScores(scoreMap);
    } catch (e) {
      console.error("Failed to fetch imported repos", e);
    } finally {
      if (!silent) setLoadingImported(false);
    }
  };

  useEffect(() => {
    void fetchImportedRepositories();
  }, []);

  // 2. Fetch GitHub repositories if the tab is opened
  const fetchGithubRepositories = useCallback(async () => {
    setLoadingGithub(true);
    setGithubError(null);
    try {
      const res = await apiClient.getGithubRepos();
      setGithubRepos(res.repositories);
    } catch (e) {
      console.error("Failed to fetch GitHub repos", e);
      if (e instanceof ApiError) {
        setGithubError(e.message);
      } else {
        setGithubError("Failed to load repositories from GitHub. Make sure your token is valid.");
      }
    } finally {
      setLoadingGithub(false);
    }
  }, []);

  useEffect(() => {
    if (activeTab === "github" && githubRepos.length === 0) {
      void fetchGithubRepositories();
    }
  }, [activeTab, githubRepos.length, fetchGithubRepositories]);

  // 3. Polling effect if there are any repos in active analysis state
  const isPollingNeeded = useMemo(() => {
    return Object.values(analysisStatuses).some(
      (status) => ["queued", "cloning", "analyzing"].includes(status)
    );
  }, [analysisStatuses]);

  useEffect(() => {
    let intervalId: NodeJS.Timeout;
    if (isPollingNeeded) {
      intervalId = setInterval(() => {
        void fetchImportedRepositories(true);
      }, 3000);
    }
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [isPollingNeeded]);

  // 4. Import action
  const handleImport = async (githubRepoId: number) => {
    setImportingRepoId(githubRepoId);
    try {
      await apiClient.importRepository(githubRepoId);
      // Force refresh imported repositories list
      await fetchImportedRepositories(true);
      setActiveTab("imported");
    } catch (e) {
      alert(e instanceof Error ? e.message : "Failed to import repository");
    } finally {
      setImportingRepoId(null);
    }
  };

  // Filter lists
  const filteredGithubRepos = useMemo(() => {
    return githubRepos.filter((repo) =>
      repo.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      repo.owner.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [githubRepos, searchQuery]);

  const filteredImportedRepos = useMemo(() => {
    return importedRepos.filter((repo) =>
      repo.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      repo.owner.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [importedRepos, searchQuery]);

  // Helper for status badges
  const renderStatusBadge = (repoId: number) => {
    const status = analysisStatuses[repoId] || "queued";
    
    switch (status) {
      case "completed":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle className="h-3 w-3" /> Ready
          </span>
        );
      case "failed":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <AlertCircle className="h-3 w-3" /> Analysis Failed
          </span>
        );
      case "cloning":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-sky-500/10 text-sky-400 border border-sky-500/20 animate-pulse">
            <Spinner className="h-3 w-3 text-sky-400" /> Cloning...
          </span>
        );
      case "analyzing":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-violet-500/10 text-violet-400 border border-violet-500/20 animate-pulse">
            <Spinner className="h-3 w-3 text-violet-400" /> Analyzing...
          </span>
        );
      case "queued":
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse">
            <Spinner className="h-3 w-3 text-amber-400" /> Queued
          </span>
        );
    }
  };

  const getScoreColorClass = (score: number | null) => {
    if (score === null) return "text-muted-foreground";
    if (score >= 80) return "text-emerald-400";
    if (score >= 50) return "text-amber-400";
    return "text-rose-400";
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Dynamic Background Gradients */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-indigo-500/10 rounded-full filter blur-3xl -z-10" />
      <div className="absolute top-1/3 right-1/4 w-96 h-96 bg-violet-500/10 rounded-full filter blur-3xl -z-10" />

      {/* Main Container */}
      <main className="flex-1 max-w-5xl w-full mx-auto px-4 py-8 flex flex-col md:flex-row gap-8">
        
        {/* Left Side: Profile info */}
        <aside className="w-full md:w-80 flex flex-col gap-6 shrink-0">
          <header className="space-y-1">
            <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-indigo-400 via-violet-400 to-purple-400 bg-clip-text text-transparent">
              SkillLedger
            </h1>
            <p className="text-sm text-slate-400">
              Repository Intelligence Engine
            </p>
          </header>
          
          <UserProfileCard onLogout={() => router.replace("/login")} />
          
          {user && (
            <div className="p-4 bg-slate-900/50 backdrop-blur-md rounded-xl border border-slate-800 space-y-4">
              <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
                <Settings className="h-4 w-4 text-indigo-400" /> Account Stats
              </h3>
              <dl className="grid grid-cols-2 gap-y-2 text-xs font-medium">
                <dt className="text-slate-400">User ID</dt>
                <dd className="text-right font-mono text-indigo-300">{user.id}</dd>
                <dt className="text-slate-400">GitHub ID</dt>
                <dd className="text-right font-mono text-indigo-300">{user.github_id}</dd>
                <dt className="text-slate-400">Imported Repos</dt>
                <dd className="text-right text-indigo-300">{importedRepos.length}</dd>
                <dt className="text-slate-400">Registered At</dt>
                <dd className="text-right text-indigo-300">
                  {new Date(user.created_at).toLocaleDateString()}
                </dd>
              </dl>
            </div>
          )}
        </aside>

        {/* Right Side: Repositories dashboard */}
        <section className="flex-1 flex flex-col gap-6 min-w-0">
          
          {/* Search bar & Tabs */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            
            {/* Tabs */}
            <div className="flex bg-slate-900/80 p-1 rounded-lg border border-slate-800 self-start">
              <button
                onClick={() => { setActiveTab("imported"); setSearchQuery(""); }}
                className={`px-4 py-2 text-xs font-semibold rounded-md transition-all duration-200 ${
                  activeTab === "imported"
                    ? "bg-indigo-600 text-white shadow-lg"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Imported ({importedRepos.length})
              </button>
              <button
                onClick={() => { setActiveTab("github"); setSearchQuery(""); }}
                className={`px-4 py-2 text-xs font-semibold rounded-md transition-all duration-200 ${
                  activeTab === "github"
                    ? "bg-indigo-600 text-white shadow-lg"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Import From GitHub
              </button>
            </div>

            {/* Search Input */}
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
              <input
                type="text"
                placeholder={activeTab === "imported" ? "Search imported repos..." : "Search GitHub repos..."}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-4 py-2 text-sm bg-slate-900/60 border border-slate-800 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
              />
            </div>
          </div>

          {/* TAB 1: IMPORTED REPOSITORIES */}
          {activeTab === "imported" && (
            <div className="space-y-4">
              {loadingImported ? (
                <div className="flex flex-col items-center justify-center py-20 gap-3">
                  <Spinner className="h-8 w-8 text-indigo-500" />
                  <p className="text-sm text-slate-400">Loading your imported repositories...</p>
                </div>
              ) : filteredImportedRepos.length === 0 ? (
                <div className="p-8 text-center bg-slate-900/30 rounded-xl border border-dashed border-slate-800">
                  <GitBranch className="h-10 w-10 text-slate-600 mx-auto mb-3" />
                  <h3 className="font-semibold text-slate-300">No repositories imported yet</h3>
                  <p className="text-sm text-slate-400 mt-1 max-w-md mx-auto">
                    Import repositories from your GitHub account to generate detailed cyclomatic complexity, security, and developer metrics reports.
                  </p>
                  <button
                    onClick={() => setActiveTab("github")}
                    className="mt-4 px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg shadow-md transition-colors"
                  >
                    Browse GitHub Repositories
                  </button>
                </div>
              ) : (
                <div className="grid gap-4">
                  {filteredImportedRepos.map((repo) => {
                    const status = analysisStatuses[repo.id] || "queued";
                    const scores = analysisScores[repo.id] || { complexity: null, security: null, documentation: null };
                    
                    return (
                      <div
                        key={repo.id}
                        className="group relative p-5 bg-slate-900/40 hover:bg-slate-900/70 backdrop-blur-sm border border-slate-800 hover:border-slate-700 rounded-xl transition-all duration-300"
                      >
                        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 mb-4">
                          <div>
                            <div className="flex items-center gap-2.5 mb-1.5">
                              <h3 className="text-base font-bold text-slate-200 group-hover:text-indigo-400 transition-colors">
                                {repo.name}
                              </h3>
                              {renderStatusBadge(repo.id)}
                            </div>
                            <p className="text-xs text-slate-400 flex items-center gap-1.5">
                              <span className="font-semibold text-slate-300">{repo.owner}</span>
                              <span className="text-slate-600">•</span>
                              <span>default branch: <span className="font-mono text-indigo-300">{repo.default_branch}</span></span>
                            </p>
                            {repo.description && (
                              <p className="text-xs text-slate-400 mt-2 line-clamp-1 italic max-w-xl">
                                {repo.description}
                              </p>
                            )}
                          </div>

                          <div className="flex items-center gap-2 shrink-0">
                            {status === "completed" ? (
                              <>
                                <button
                                  onClick={() => router.push(`/repositories/${repo.id}` as Route)}
                                  className="px-3.5 py-1.5 text-xs font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg flex items-center gap-1.5 transition-colors"
                                >
                                  <Eye className="h-3.5 w-3.5" /> Details
                                </button>
                                <button
                                  onClick={() => router.push(`/repositories/${repo.id}/analysis` as Route)}
                                  className="px-3.5 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg flex items-center gap-1.5 shadow-md shadow-indigo-600/10 transition-colors"
                                >
                                  <Activity className="h-3.5 w-3.5" /> Report
                                </button>
                              </>
                            ) : status === "failed" ? (
                              <button
                                onClick={() => handleImport(repo.github_repo_id)}
                                className="px-3.5 py-1.5 text-xs font-semibold text-white bg-rose-600 hover:bg-rose-500 border border-rose-500 rounded-lg flex items-center gap-1.5 transition-colors"
                              >
                                <RefreshCw className="h-3.5 w-3.5" /> Retry Scan
                              </button>
                            ) : (
                              <div className="text-xs font-semibold text-slate-500 animate-pulse flex items-center gap-1.5">
                                Scanning code...
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Analysis Scores Quick View */}
                        {status === "completed" && (
                          <div className="grid grid-cols-3 gap-4 pt-4 border-t border-slate-800/60 text-xs">
                            <div className="flex items-center gap-2">
                              <div className="p-1.5 rounded bg-indigo-500/10 text-indigo-400">
                                <Activity className="h-3.5 w-3.5" />
                              </div>
                              <div>
                                <p className="text-slate-400 font-medium">Complexity</p>
                                <p className={`font-bold ${getScoreColorClass(scores.complexity)}`}>
                                  {scores.complexity !== null ? `${scores.complexity}/100` : "N/A"}
                                </p>
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              <div className="p-1.5 rounded bg-violet-500/10 text-violet-400">
                                <Shield className="h-3.5 w-3.5" />
                              </div>
                              <div>
                                <p className="text-slate-400 font-medium">Security</p>
                                <p className={`font-bold ${getScoreColorClass(scores.security)}`}>
                                  {scores.security !== null ? `${scores.security}/100` : "N/A"}
                                </p>
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              <div className="p-1.5 rounded bg-purple-500/10 text-purple-400">
                                <FileText className="h-3.5 w-3.5" />
                              </div>
                              <div>
                                <p className="text-slate-400 font-medium">Documentation</p>
                                <p className={`font-bold ${getScoreColorClass(scores.documentation)}`}>
                                  {scores.documentation !== null ? `${scores.documentation}/100` : "N/A"}
                                </p>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* TAB 2: IMPORT FROM GITHUB */}
          {activeTab === "github" && (
            <div className="space-y-4">
              {githubError && (
                <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-400 text-xs font-semibold flex items-start gap-2.5">
                  <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                  <div>
                    <p className="font-bold">Fetch Error</p>
                    <p className="font-normal mt-0.5">{githubError}</p>
                    <button
                      onClick={fetchGithubRepositories}
                      className="mt-2 text-indigo-400 hover:text-indigo-300 underline font-bold"
                    >
                      Click here to try again
                    </button>
                  </div>
                </div>
              )}

              {loadingGithub ? (
                <div className="flex flex-col items-center justify-center py-20 gap-3">
                  <Spinner className="h-8 w-8 text-indigo-500" />
                  <p className="text-sm text-slate-400">Fetching repositories from GitHub...</p>
                </div>
              ) : filteredGithubRepos.length === 0 && !githubError ? (
                <div className="p-8 text-center bg-slate-900/30 rounded-xl border border-slate-800">
                  <Github className="h-10 w-10 text-slate-600 mx-auto mb-3" />
                  <p className="text-sm text-slate-400">No GitHub repositories found matching your query.</p>
                </div>
              ) : (
                <div className="grid gap-3 max-h-[600px] overflow-y-auto pr-1">
                  {filteredGithubRepos.map((repo) => {
                    const isAlreadyImported = importedRepos.some(
                      (ir) => ir.github_repo_id === repo.github_id
                    );
                    const isCurrentlyImporting = importingRepoId === repo.github_id;
                    const latestStatus = importedRepos.find(
                      (ir) => ir.github_repo_id === repo.github_id
                    )?.id ? analysisStatuses[importedRepos.find((ir) => ir.github_repo_id === repo.github_id)!.id] : undefined;

                    return (
                      <div
                        key={repo.github_id}
                        className="flex items-center justify-between p-4 bg-slate-900/30 hover:bg-slate-900/60 border border-slate-800 hover:border-slate-800 rounded-xl transition-all"
                      >
                        <div>
                          <div className="flex items-center gap-2">
                            <h4 className="text-sm font-bold text-slate-200">
                              {repo.name}
                            </h4>
                            {repo.private && (
                              <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-400 font-semibold border border-slate-700">
                                Private
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-slate-500 mt-0.5">
                            {repo.owner}
                          </p>
                          <div className="flex items-center gap-3 mt-2 text-[10px] text-slate-400 font-medium">
                            {repo.language && (
                              <span className="flex items-center gap-1">
                                <span className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
                                {repo.language}
                              </span>
                            )}
                            <span className="flex items-center gap-1">
                              <Star className="h-3 w-3 text-amber-500/80" /> {repo.stars} stars
                            </span>
                          </div>
                        </div>

                        <button
                          disabled={isCurrentlyImporting}
                          onClick={() => handleImport(repo.github_id)}
                          className={`px-3.5 py-1.5 text-xs font-semibold rounded-lg flex items-center gap-1.5 transition-colors ${
                            isAlreadyImported
                              ? latestStatus === "completed"
                                ? "bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700"
                                : "bg-indigo-600/30 text-indigo-300 border border-indigo-500/20"
                              : "bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/10"
                          }`}
                        >
                          {isCurrentlyImporting ? (
                            <>
                              <Spinner className="h-3 w-3" /> Importing...
                            </>
                          ) : isAlreadyImported ? (
                            latestStatus === "completed" ? (
                              <>
                                <RefreshCw className="h-3 w-3" /> Re-scan
                              </>
                            ) : (
                              <>
                                <Spinner className="h-3 w-3" /> Scanning...
                              </>
                            )
                          ) : (
                            <>
                              <Download className="h-3 w-3" /> Import
                            </>
                          )}
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <Suspense
        fallback={
          <div className="flex min-h-screen items-center justify-center bg-slate-950">
            <Spinner className="h-8 w-8 text-indigo-500" />
          </div>
        }
      >
        <DashboardContent />
      </Suspense>
    </ProtectedRoute>
  );
}

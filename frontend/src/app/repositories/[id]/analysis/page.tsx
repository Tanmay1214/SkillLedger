"use client";

import { useParams, useRouter } from "next/navigation";
import type { Route } from "next";
import { useEffect, useState } from "react";
import { 
  ArrowLeft, 
  Activity, 
  Shield, 
  FileText, 
  GitCommit, 
  CheckCircle2, 
  XCircle,
  Terminal,
  Clock,
  Sparkles
} from "lucide-react";

import { ProtectedRoute } from "@/components/auth/protected-route";
import { Spinner } from "@/components/ui/spinner";
import { apiClient } from "@/lib/api-client";
import type { RepositoryAnalysisReport } from "@/types/repositories";

export default function AnalysisReportPage() {
  const params = useParams();
  const router = useRouter();
  const repoId = Number(params.id);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<RepositoryAnalysisReport | null>(null);
  const [activeTab, setActiveTab] = useState<"security" | "complexity" | "documentation" | "commits">("security");

  useEffect(() => {
    const fetchAnalysis = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await apiClient.getRepositoryAnalysis(repoId);
        setReport(data);
      } catch (e) {
        console.error("Failed to load analysis report", e);
        setError("Failed to load repository intelligence report. Ensure analysis is completed.");
      } finally {
        setLoading(false);
      }
    };
    if (repoId) {
      void fetchAnalysis();
    }
  }, [repoId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <Spinner className="h-8 w-8 text-indigo-500" />
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-center p-6 text-center">
        <ArrowLeft 
          className="h-8 w-8 text-slate-400 cursor-pointer hover:text-indigo-400 transition-colors mb-4" 
          onClick={() => router.push(`/repositories/${repoId}` as Route)}
        />
        <h2 className="text-xl font-bold text-rose-400">Error Loading Report</h2>
        <p className="text-slate-400 text-sm mt-2 max-w-md">{error || "Repository report not found."}</p>
        <button
          onClick={() => router.push(`/repositories/${repoId}` as Route)}
          className="mt-6 px-4 py-2 text-xs font-semibold bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-lg text-slate-200 transition-colors"
        >
          Return to Details
        </button>
      </div>
    );
  }

  if (report.analysis_status !== "completed") {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-center p-6 text-center">
        <Clock className="h-10 w-10 text-indigo-500 animate-spin mb-4" />
        <h2 className="text-xl font-bold text-slate-200">Analysis in Progress</h2>
        <p className="text-slate-400 text-sm mt-2 max-w-md">
          This repository is still being analyzed. Status: <span className="font-semibold text-indigo-400">{report.analysis_status}</span>.
        </p>
        <button
          onClick={() => router.push("/dashboard")}
          className="mt-6 px-4 py-2 text-xs font-semibold bg-indigo-650 hover:bg-indigo-600 rounded-lg text-white transition-colors"
        >
          Go to Dashboard
        </button>
      </div>
    );
  }

  const { repository, security_findings, complexity_metrics, documentation_report, commits_metrics } = report;

  const getScoreColorClass = (score: number | null) => {
    if (score === null) return "text-slate-500 border-slate-800/40 bg-slate-900/10";
    if (score >= 80) return "text-emerald-400 border-emerald-500/20 bg-emerald-500/5";
    if (score >= 50) return "text-amber-400 border-amber-500/20 bg-amber-500/5";
    return "text-rose-400 border-rose-500/20 bg-rose-500/5";
  };

  const getSeverityBadge = (severity: string) => {
    if (severity === "high") {
      return (
        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/10 text-rose-400 border border-rose-500/20">
          High
        </span>
      );
    }
    return (
      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">
        Medium
      </span>
    );
  };

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
        {/* Dynamic Background Gradients */}
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-indigo-500/10 rounded-full filter blur-3xl -z-10" />
        <div className="absolute top-1/2 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full filter blur-3xl -z-10" />

        {/* Navbar */}
        <nav className="border-b border-slate-900 bg-slate-950/60 backdrop-blur-md sticky top-0 z-10 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.push(`/repositories/${repoId}` as Route)}
              className="p-2 bg-slate-900 hover:bg-slate-850 border border-slate-800 rounded-lg text-slate-400 hover:text-slate-200 transition-colors"
            >
              <ArrowLeft className="h-4 w-4" />
            </button>
            <div>
              <h2 className="text-base font-extrabold text-slate-200">
                Repository Intelligence Report
              </h2>
              <p className="text-xs text-slate-400">{repository.name} by {repository.owner}</p>
            </div>
          </div>
          
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 text-xs font-bold border border-emerald-500/20">
            <Sparkles className="h-3.5 w-3.5 animate-pulse" /> Complete
          </div>
        </nav>

        {/* Content Wrapper */}
        <div className="flex-1 max-w-5xl w-full mx-auto px-4 py-8 space-y-8">
          
          {/* Executive Scores Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            
            {/* Security Card */}
            <div 
              onClick={() => setActiveTab("security")}
              className={`p-5 rounded-xl border cursor-pointer transition-all duration-300 flex items-center justify-between ${
                activeTab === "security"
                  ? "border-violet-500 bg-slate-900/60 shadow-lg shadow-violet-500/5 scale-[1.02]"
                  : "border-slate-850 bg-slate-900/30 hover:bg-slate-900/50"
              }`}
            >
              <div className="space-y-1">
                <span className="text-xs text-slate-400 font-semibold flex items-center gap-1.5">
                  <Shield className="h-3.5 w-3.5 text-violet-400" /> Security
                </span>
                <p className="text-xs text-slate-500 font-medium">Vulnerabilities & Secrets</p>
              </div>
              <div className={`w-14 h-14 rounded-full border flex items-center justify-center text-base font-extrabold ${getScoreColorClass(report.security_score)}`}>
                {report.security_score !== null ? `${report.security_score}` : "N/A"}
              </div>
            </div>

            {/* Complexity Card */}
            <div 
              onClick={() => setActiveTab("complexity")}
              className={`p-5 rounded-xl border cursor-pointer transition-all duration-300 flex items-center justify-between ${
                activeTab === "complexity"
                  ? "border-indigo-500 bg-slate-900/60 shadow-lg shadow-indigo-500/5 scale-[1.02]"
                  : "border-slate-850 bg-slate-900/30 hover:bg-slate-900/50"
              }`}
            >
              <div className="space-y-1">
                <span className="text-xs text-slate-400 font-semibold flex items-center gap-1.5">
                  <Activity className="h-3.5 w-3.5 text-indigo-400" /> Complexity
                </span>
                <p className="text-xs text-slate-500 font-medium">Lizard Cyclomatic Scan</p>
              </div>
              <div className={`w-14 h-14 rounded-full border flex items-center justify-center text-base font-extrabold ${getScoreColorClass(report.complexity_score)}`}>
                {report.complexity_score !== null ? `${report.complexity_score}` : "N/A"}
              </div>
            </div>

            {/* Documentation Card */}
            <div 
              onClick={() => setActiveTab("documentation")}
              className={`p-5 rounded-xl border cursor-pointer transition-all duration-300 flex items-center justify-between ${
                activeTab === "documentation"
                  ? "border-purple-500 bg-slate-900/60 shadow-lg shadow-purple-500/5 scale-[1.02]"
                  : "border-slate-850 bg-slate-900/30 hover:bg-slate-900/50"
              }`}
            >
              <div className="space-y-1">
                <span className="text-xs text-slate-400 font-semibold flex items-center gap-1.5">
                  <FileText className="h-3.5 w-3.5 text-purple-400" /> Documentation
                </span>
                <p className="text-xs text-slate-500 font-medium">Checklist & README Scan</p>
              </div>
              <div className={`w-14 h-14 rounded-full border flex items-center justify-center text-base font-extrabold ${getScoreColorClass(report.documentation_score)}`}>
                {report.documentation_score !== null ? `${report.documentation_score}` : "N/A"}
              </div>
            </div>
          </div>

          {/* Sub Navigation Tabs */}
          <div className="flex bg-slate-900/80 p-1 rounded-lg border border-slate-850 max-w-lg">
            {(["security", "complexity", "documentation", "commits"] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`flex-1 py-2 text-xs font-bold rounded-md transition-all duration-200 capitalize ${
                  activeTab === tab
                    ? "bg-indigo-650 text-white shadow"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {tab === "security" ? "Vulnerabilities" : tab}
              </button>
            ))}
          </div>

          {/* TAB CONTENT: SECURITY VULNERABILITIES */}
          {activeTab === "security" && (
            <div className="space-y-4">
              <div className="p-6 bg-slate-900/40 border border-slate-800 rounded-xl space-y-4">
                <h3 className="text-base font-bold text-slate-300 flex items-center gap-2">
                  <Shield className="h-5 w-5 text-indigo-400" /> Security Vulnerability Scanner
                </h3>
                
                {security_findings === null || security_findings.length === 0 ? (
                  <div className="p-8 text-center bg-slate-950/20 border border-slate-850 rounded-xl">
                    <CheckCircle2 className="h-8 w-8 text-emerald-500 mx-auto mb-2" />
                    <h4 className="font-semibold text-slate-350">Zero vulnerabilities found</h4>
                    <p className="text-xs text-slate-500 mt-1">Excellent! No hardcoded keys, passwords, SQL injections, or unsafe CLI subprocesses were detected.</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <p className="text-xs text-slate-400 font-medium">
                      Found {security_findings.length} potential vulnerabilities in your codebase.
                    </p>
                    <div className="space-y-3.5 max-h-[500px] overflow-y-auto pr-1">
                      {security_findings.map((f, idx) => (
                        <div
                          key={idx}
                          className="p-4 bg-slate-950/40 border border-slate-850 rounded-xl space-y-2 hover:border-slate-700 transition"
                        >
                          <div className="flex items-center justify-between gap-4">
                            <h4 className="text-sm font-extrabold text-slate-200 flex items-center gap-2">
                              {f.title}
                            </h4>
                            {getSeverityBadge(f.severity)}
                          </div>
                          
                          <p className="text-xs text-slate-400 font-semibold flex items-center gap-1">
                            File: <span className="font-mono text-indigo-300">{f.file}</span> 
                            <span className="text-slate-600">:</span> 
                            Line: <span className="font-mono text-indigo-300">{f.line}</span>
                          </p>

                          <p className="text-xs text-slate-400 font-normal leading-relaxed italic bg-slate-950/80 p-2 rounded border border-slate-900 mt-2">
                            {f.description}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB CONTENT: COMPLEXITY & Lizard */}
          {activeTab === "complexity" && (
            <div className="space-y-4">
              <div className="p-6 bg-slate-900/40 border border-slate-800 rounded-xl space-y-6">
                <div className="flex items-center justify-between">
                  <h3 className="text-base font-bold text-slate-300 flex items-center gap-2">
                    <Activity className="h-5 w-5 text-indigo-400" /> Cyclomatic Complexity Stats
                  </h3>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                    Engine: Lizard
                  </span>
                </div>

                {complexity_metrics && (
                  <>
                    {/* General Metrics Grid */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 p-4 bg-slate-950/40 border border-slate-850 rounded-xl text-center">
                      <div>
                        <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Total LOC</p>
                        <p className="text-xl font-extrabold text-slate-100 mt-1">{complexity_metrics.total_loc}</p>
                      </div>
                      <div>
                        <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Avg Complexity</p>
                        <p className="text-xl font-extrabold text-indigo-400 mt-1">{complexity_metrics.average_complexity}</p>
                      </div>
                      <div>
                        <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Max Complexity</p>
                        <p className="text-xl font-extrabold text-violet-400 mt-1">{complexity_metrics.max_complexity}</p>
                      </div>
                      <div>
                        <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Functions Count</p>
                        <p className="text-xl font-extrabold text-purple-400 mt-1">{complexity_metrics.function_count}</p>
                      </div>
                    </div>

                    {/* Complex Functions */}
                    <div className="space-y-3">
                      <h4 className="text-xs font-bold text-slate-350">Complex Functions & Files (Complexity &gt; 10)</h4>
                      
                      {complexity_metrics.complex_functions.length === 0 ? (
                        <div className="p-6 text-center bg-slate-950/10 border border-slate-850 rounded-xl text-xs text-slate-500 italic">
                          No highly complex functions detected. Your codebase is extremely modular!
                        </div>
                      ) : (
                        <div className="space-y-3 max-h-[300px] overflow-y-auto pr-1">
                          {complexity_metrics.complex_functions.map((fn, idx) => (
                            <div
                              key={idx}
                              className="p-3 bg-slate-950/30 border border-slate-850 rounded-xl flex items-center justify-between text-xs"
                            >
                              <div className="min-w-0">
                                <h5 className="font-extrabold text-slate-200 truncate">
                                  {fn.function}()
                                </h5>
                                <p className="text-[10px] text-slate-500 truncate mt-0.5">
                                  file: <span className="font-mono text-slate-400">{fn.file}</span>
                                </p>
                              </div>
                              <div className="flex gap-4 items-center shrink-0">
                                <div className="text-right">
                                  <p className="font-bold text-slate-300">{fn.loc} lines</p>
                                  <p className="text-[10px] text-slate-500">{fn.parameter_count} params</p>
                                </div>
                                <span className="px-2.5 py-1 bg-rose-500/10 text-rose-400 border border-rose-500/20 rounded font-bold">
                                  CC: {fn.complexity}
                                </span>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </>
                )}
              </div>
            </div>
          )}

          {/* TAB CONTENT: DOCUMENTATION CHECKLIST */}
          {activeTab === "documentation" && (
            <div className="space-y-4">
              <div className="p-6 bg-slate-900/40 border border-slate-800 rounded-xl space-y-6">
                <h3 className="text-base font-bold text-slate-300 flex items-center gap-2">
                  <FileText className="h-5 w-5 text-indigo-400" /> Documentation Audit Report
                </h3>

                {documentation_report && (
                  <div className="space-y-6">
                    {/* Checklist */}
                    <div className="space-y-3 max-w-md">
                      <h4 className="text-xs font-bold text-slate-350">README Audit Checklist</h4>
                      
                      <div className="space-y-2">
                        {/* Requirement 1 */}
                        <div className="flex items-center justify-between p-3 bg-slate-950/40 border border-slate-850 rounded-lg text-xs font-semibold">
                          <span className="text-slate-350">README File Exists</span>
                          {documentation_report.checklist.readme_exists ? (
                            <span className="text-emerald-400 flex items-center gap-1">
                              <CheckCircle2 className="h-4 w-4" /> Detected
                            </span>
                          ) : (
                            <span className="text-rose-400 flex items-center gap-1">
                              <XCircle className="h-4 w-4" /> Missing
                            </span>
                          )}
                        </div>

                        {/* Requirement 2 */}
                        <div className="flex items-center justify-between p-3 bg-slate-950/40 border border-slate-850 rounded-lg text-xs font-semibold">
                          <span className="text-slate-350">Installation instructions</span>
                          {documentation_report.checklist.installation_instructions ? (
                            <span className="text-emerald-400 flex items-center gap-1">
                              <CheckCircle2 className="h-4 w-4" /> Detected
                            </span>
                          ) : (
                            <span className="text-rose-400 flex items-center gap-1">
                              <XCircle className="h-4 w-4" /> Missing
                            </span>
                          )}
                        </div>

                        {/* Requirement 3 */}
                        <div className="flex items-center justify-between p-3 bg-slate-950/40 border border-slate-850 rounded-lg text-xs font-semibold">
                          <span className="text-slate-350">Usage Guide & Examples</span>
                          {documentation_report.checklist.usage_guide ? (
                            <span className="text-emerald-400 flex items-center gap-1">
                              <CheckCircle2 className="h-4 w-4" /> Detected
                            </span>
                          ) : (
                            <span className="text-rose-400 flex items-center gap-1">
                              <XCircle className="h-4 w-4" /> Missing
                            </span>
                          )}
                        </div>

                        {/* Requirement 4 */}
                        <div className="flex items-center justify-between p-3 bg-slate-950/40 border border-slate-850 rounded-lg text-xs font-semibold">
                          <span className="text-slate-350">Features / Capability List</span>
                          {documentation_report.checklist.features_list ? (
                            <span className="text-emerald-400 flex items-center gap-1">
                              <CheckCircle2 className="h-4 w-4" /> Detected
                            </span>
                          ) : (
                            <span className="text-rose-400 flex items-center gap-1">
                              <XCircle className="h-4 w-4" /> Missing
                            </span>
                          )}
                        </div>

                        {/* Requirement 5 */}
                        <div className="flex items-center justify-between p-3 bg-slate-950/40 border border-slate-850 rounded-lg text-xs font-semibold">
                          <span className="text-slate-350">Contributing Guidelines / License</span>
                          {documentation_report.checklist.contribution_guidelines ? (
                            <span className="text-emerald-400 flex items-center gap-1">
                              <CheckCircle2 className="h-4 w-4" /> Detected
                            </span>
                          ) : (
                            <span className="text-rose-400 flex items-center gap-1">
                              <XCircle className="h-4 w-4" /> Missing
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Metadata */}
                    <div className="p-4 bg-slate-950/30 border border-slate-850 rounded-xl text-xs space-y-1 max-w-md">
                      <p className="text-slate-450">
                        File Audited: <span className="font-mono text-indigo-400 font-bold">{documentation_report.readme_filename || "None"}</span>
                      </p>
                      <p className="text-slate-450">
                        README Length: <span className="font-bold text-slate-300">{documentation_report.length} characters</span>
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB CONTENT: COMMIT HISTORY */}
          {activeTab === "commits" && (
            <div className="space-y-4">
              <div className="p-6 bg-slate-900/40 border border-slate-800 rounded-xl space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-base font-bold text-slate-300 flex items-center gap-2">
                    <GitCommit className="h-5 w-5 text-indigo-400" /> Git Commit Timeline
                  </h3>
                  {commits_metrics && (
                    <span className="text-xs font-bold text-slate-400 bg-slate-950 px-2.5 py-1 rounded border border-slate-850">
                      Total: {commits_metrics.total_commits} commits
                    </span>
                  )}
                </div>

                {commits_metrics && (
                  <div className="space-y-3.5 max-h-[500px] overflow-y-auto pr-1">
                    {commits_metrics.commits.map((c, idx) => (
                      <div
                        key={idx}
                        className="p-3 bg-slate-950/50 border border-slate-850/60 hover:border-slate-800 rounded-xl flex gap-3 text-xs"
                      >
                        <div className="p-2 rounded bg-indigo-500/10 text-indigo-400 h-8 shrink-0 flex items-center justify-center font-mono">
                          <Terminal className="h-3.5 w-3.5" />
                        </div>
                        <div className="min-w-0 flex-1 space-y-1">
                          <div className="flex items-center justify-between gap-4">
                            <span className="font-extrabold text-slate-200 truncate">{c.author}</span>
                            <span className="font-mono text-[10px] text-slate-500 shrink-0">{c.sha}</span>
                          </div>
                          <p className="text-slate-300 leading-relaxed font-normal">{c.message}</p>
                          {c.date && (
                            <p className="text-[10px] text-slate-500">
                              committed at: {new Date(c.date).toLocaleString()}
                            </p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </ProtectedRoute>
  );
}

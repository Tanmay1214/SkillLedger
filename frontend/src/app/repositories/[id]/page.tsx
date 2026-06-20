"use client";

import { useParams, useRouter } from "next/navigation";
import type { Route } from "next";
import { useEffect, useState, useMemo } from "react";
import { 
  ArrowLeft, 
  GitBranch, 
  Star, 
  Eye, 
  GitFork, 
  Activity, 
  Users, 
  Layers, 
  Code,
  Search,
  ExternalLink,
  BookOpen,
  Globe,
  Lock,
  ShieldCheck,
  Wifi,
  AlertCircle,
  Server,
  CheckCircle2,
  RefreshCw,
  Award,
  Cpu,
  Brain,
  Tag,
  ListChecks
} from "lucide-react";

import { ProtectedRoute } from "@/components/auth/protected-route";
import { Spinner } from "@/components/ui/spinner";
import { apiClient } from "@/lib/api-client";
import type { RepositoryAnalysisReport } from "@/types/repositories";
import type { DeploymentReportResponse } from "@/types/deployments";
import type { Skill, ProjectInsight } from "@/types/skills_insights";
import type { Contributor, ModuleOwnership, ContributionReport } from "@/types/contributions";
import { 
  ResponsiveContainer, 
  PieChart, 
  Pie, 
  Cell, 
  Tooltip as ChartTooltip, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid 
} from "recharts";
import { TrendingUp, BarChart2 } from "lucide-react";

const CHART_COLORS = [
  "#6366f1",
  "#8b5cf6",
  "#d946ef",
  "#ec4899",
  "#f43f5e",
  "#10b981",
  "#3b82f6"
];

export default function RepositoryDetailsPage() {
  const params = useParams();
  const router = useRouter();
  const repoId = Number(params.id);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<RepositoryAnalysisReport | null>(null);
  const [depSearchQuery, setDepSearchQuery] = useState("");
  const [contribSortBy, setContribSortBy] = useState<"commits" | "percentage">("commits");
  const [activeSection, setActiveSection] = useState<"overview" | "analytics">("overview");
  const [isClient, setIsClient] = useState(false);

  // Contribution Verification States
  const [contribReport, setContribReport] = useState<ContributionReport | null>(null);
  const [contributorsList, setContributorsList] = useState<Contributor[] | null>(null);
  const [ownershipBreakdown, setOwnershipBreakdown] = useState<ModuleOwnership[] | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  useEffect(() => {
    const fetchContributionData = async () => {
      try {
        const [rep, list, owner] = await Promise.all([
          apiClient.getContributionReport(repoId),
          apiClient.getContributors(repoId),
          apiClient.getOwnershipBreakdown(repoId)
        ]);
        setContribReport(rep);
        setContributorsList(list);
        setOwnershipBreakdown(owner);
      } catch (e) {
        // Silent failure / expected if no report run yet
        console.log("No contribution report yet:", e);
      }
    };
    if (repoId && report) {
      void fetchContributionData();
    }
  }, [repoId, report]);

  const handleAnalyzeContributions = async () => {
    setAnalyzing(true);
    setAnalysisError(null);
    try {
      await apiClient.analyzeContributions(repoId);
      // Poll every 2s for up to 30 attempts (60s)
      let attempts = 0;
      const interval = setInterval(async () => {
        attempts++;
        try {
          const rep = await apiClient.getContributionReport(repoId);
          if (rep) {
            clearInterval(interval);
            const [list, owner] = await Promise.all([
              apiClient.getContributors(repoId),
              apiClient.getOwnershipBreakdown(repoId)
            ]);
            setContribReport(rep);
            setContributorsList(list);
            setOwnershipBreakdown(owner);
            setAnalyzing(false);
          }
        } catch {
          if (attempts >= 30) {
            clearInterval(interval);
            setAnalysisError("Contribution analysis is taking longer than expected. Please refresh the page in a moment.");
            setAnalyzing(false);
          }
        }
      }, 2000);
    } catch (e) {
      setAnalysisError(e instanceof Error ? e.message : "Failed to trigger contribution analysis.");
      setAnalyzing(false);
    }
  };

  useEffect(() => {
    setIsClient(true);
    const fetchDetails = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await apiClient.getRepositoryAnalysis(repoId);
        setReport(data);
      } catch (e) {
        console.error("Failed to load repo details", e);
        setError("Failed to load repository details. Ensure you have access.");
      } finally {
        setLoading(false);
      }
    };
    if (repoId) {
      void fetchDetails();
    }
  }, [repoId]);

  // Filter dependencies
  const filteredDeps = useMemo(() => {
    if (!report) return [];
    return report.dependencies.filter((dep) =>
      dep.dependency_name.toLowerCase().includes(depSearchQuery.toLowerCase())
    );
  }, [report, depSearchQuery]);

  // Sort contributors
  const sortedContributors = useMemo(() => {
    if (!report) return [];
    return [...report.contributors].sort((a, b) => {
      if (contribSortBy === "commits") {
        return b.commits - a.commits;
      } else {
        return b.ownership_percentage - a.ownership_percentage;
      }
    });
  }, [report, contribSortBy]);

  // Skills & Project Insights States
  const [skills, setSkills] = useState<Skill[] | null>(null);
  const [insights, setInsights] = useState<ProjectInsight | null>(null);
  const [extracting, setExtracting] = useState(false);
  const [extractError, setExtractError] = useState<string | null>(null);
  const [selectedSkillId, setSelectedSkillId] = useState<number | null>(null);

  useEffect(() => {
    const fetchSkillsAndInsights = async () => {
      try {
        const [s, ins] = await Promise.all([
          apiClient.getSkills(repoId),
          apiClient.getProjectInsights(repoId)
        ]);
        setSkills(s);
        setInsights(ins);
      } catch {
        // Silent failure if not extracted yet
      }
    };
    if (repoId && report) {
      void fetchSkillsAndInsights();
    }
  }, [repoId, report]);

  const handleExtract = async () => {
    setExtracting(true);
    setExtractError(null);
    try {
      await apiClient.extractSkills(repoId);
      // Poll every 1s for up to 5s to wait for the background task to complete
      let attempts = 0;
      const interval = setInterval(async () => {
        attempts++;
        try {
          const ins = await apiClient.getProjectInsights(repoId);
          if (ins) {
            clearInterval(interval);
            const s = await apiClient.getSkills(repoId);
            setSkills(s);
            setInsights(ins);
            setExtracting(false);
          }
        } catch {
          if (attempts >= 5) {
            clearInterval(interval);
            setExtractError("Skill extraction is taking longer than expected. Please refresh the page in a moment.");
            setExtracting(false);
          }
        }
      }, 1000);
    } catch (e) {
      setExtractError(e instanceof Error ? e.message : "Failed to trigger skill extraction.");
      setExtracting(false);
    }
  };

  const skillsByCategory = useMemo(() => {
    if (!skills) return {};
    const groups: Record<string, Skill[]> = {};
    skills.forEach((s) => {
      const catGroup = groups[s.category] || [];
      catGroup.push(s);
      groups[s.category] = catGroup;
    });
    return groups;
  }, [skills]);

  // Deployment Verification States
  const [deploymentUrl, setDeploymentUrl] = useState("");
  const [discovering, setDiscovering] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [deployReport, setDeployReport] = useState<DeploymentReportResponse | null>(null);
  const [verifyError, setVerifyError] = useState<string | null>(null);
  const [discoverMessage, setDiscoverMessage] = useState<string | null>(null);

  useEffect(() => {
    const fetchReport = async () => {
      try {
        const r = await apiClient.getDeploymentReport(repoId);
        setDeployReport(r);
        setDeploymentUrl(r.deployment_url);
      } catch {
        // Fallback to repository homepage if available
        if (report && report.repository.homepage) {
          setDeploymentUrl(report.repository.homepage);
        }
      }
    };
    if (repoId && report) {
      void fetchReport();
    }
  }, [repoId, report]);

  const handleDiscover = async () => {
    setDiscovering(true);
    setDiscoverMessage(null);
    try {
      const res = await apiClient.discoverDeployment(repoId);
      if (res.deployment_url) {
        setDeploymentUrl(res.deployment_url);
        setDiscoverMessage(`Successfully discovered via ${res.source || 'settings'}`);
      } else {
        setDiscoverMessage("No deployment URL found. Please specify it manually.");
      }
    } catch (e) {
      setDiscoverMessage(e instanceof Error ? e.message : "Discovery failed.");
    } finally {
      setDiscovering(false);
    }
  };

  const handleVerify = async () => {
    if (!deploymentUrl.trim()) {
      setVerifyError("Please enter a valid deployment URL first.");
      return;
    }
    setVerifying(true);
    setVerifyError(null);
    try {
      const r = await apiClient.verifyDeployment(repoId, deploymentUrl);
      setDeployReport(r);
    } catch (e) {
      setVerifyError(e instanceof Error ? e.message : "Verification failed.");
    } finally {
      setVerifying(false);
    }
  };

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
          onClick={() => router.push("/dashboard")}
        />
        <h2 className="text-xl font-bold text-rose-400">Error Loading Details</h2>
        <p className="text-slate-400 text-sm mt-2 max-w-md">{error || "Repository details not found."}</p>
        <button
          onClick={() => router.push("/dashboard")}
          className="mt-6 px-4 py-2 text-xs font-semibold bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-lg text-slate-200 transition-colors"
        >
          Return to Dashboard
        </button>
      </div>
    );
  }

  const { repository } = report;

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
        {/* Dynamic Background Gradients */}
        <div className="absolute top-0 right-1/4 w-96 h-96 bg-indigo-500/10 rounded-full filter blur-3xl -z-10" />
        <div className="absolute top-1/3 left-1/4 w-96 h-96 bg-violet-500/10 rounded-full filter blur-3xl -z-10" />

        {/* Top Navbar */}
        <nav className="border-b border-slate-900 bg-slate-950/60 backdrop-blur-md sticky top-0 z-10 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.push("/dashboard")}
              className="p-2 bg-slate-900 hover:bg-slate-850 border border-slate-800 rounded-lg text-slate-400 hover:text-slate-200 transition-colors"
            >
              <ArrowLeft className="h-4 w-4" />
            </button>
            <div>
              <h2 className="text-base font-extrabold text-slate-200 flex items-center gap-2">
                {repository.name}
              </h2>
              <p className="text-xs text-slate-400">{repository.owner}</p>
            </div>
          </div>
          
          <button
            onClick={() => router.push(`/repositories/${repoId}/analysis` as Route)}
            className="px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg flex items-center gap-1.5 shadow-md shadow-indigo-600/10 transition-colors"
          >
            <BookOpen className="h-3.5 w-3.5" /> View Analysis Report
          </button>
        </nav>

        {/* Content Wrapper */}
        <div className="flex-1 max-w-5xl w-full mx-auto px-4 py-8 space-y-8">
          
          {/* Header Card / Info Grid */}
          <div className="p-6 bg-slate-900/40 backdrop-blur-sm border border-slate-800 rounded-xl grid grid-cols-1 md:grid-cols-3 gap-6">
            
            {/* Metadata Info */}
            <div className="md:col-span-2 space-y-4">
              <div>
                <span className="px-2 py-0.5 rounded text-[10px] bg-indigo-500/15 text-indigo-400 font-bold border border-indigo-500/20">
                  Imported Repository
                </span>
                <h1 className="text-2xl font-bold mt-2 text-slate-100 flex items-center gap-2">
                  {repository.name}
                  <a
                    href={repository.repo_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-slate-500 hover:text-indigo-400 transition-colors"
                  >
                    <ExternalLink className="h-4 w-4" />
                  </a>
                </h1>
                {repository.description && (
                  <p className="text-sm text-slate-400 mt-2 italic font-medium">
                    {repository.description}
                  </p>
                )}
              </div>

              {/* Stats Counters */}
              <div className="flex flex-wrap items-center gap-6 text-xs text-slate-400 font-semibold pt-2">
                <span className="flex items-center gap-1.5">
                  <Star className="h-4 w-4 text-amber-500" /> {repository.stars} stars
                </span>
                <span className="flex items-center gap-1.5">
                  <GitFork className="h-4 w-4 text-sky-400" /> {repository.forks} forks
                </span>
                <span className="flex items-center gap-1.5">
                  <Eye className="h-4 w-4 text-indigo-400" /> {repository.watchers} watchers
                </span>
                <span className="flex items-center gap-1.5">
                  <GitBranch className="h-4 w-4 text-violet-400" /> <span className="font-mono text-indigo-300">{repository.default_branch}</span>
                </span>
              </div>
            </div>

            {/* Date timeline */}
            <div className="p-4 bg-slate-950/40 border border-slate-800/60 rounded-lg flex flex-col justify-center space-y-2 text-xs font-semibold">
              <div className="flex justify-between">
                <span className="text-slate-500">Language</span>
                <span className="text-indigo-400">{repository.language || "Unknown"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">First Imported</span>
                <span className="text-slate-300">
                  {new Date(repository.created_at).toLocaleDateString()}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Metadata Checked</span>
                <span className="text-slate-300">
                  {new Date(repository.updated_at).toLocaleDateString()}
                </span>
              </div>
            </div>
          </div>

          {/* Tab Navigation */}
          <div className="flex border-b border-slate-900 gap-6">
            <button
              onClick={() => setActiveSection("overview")}
              className={`pb-3 text-sm font-bold transition-all relative ${
                activeSection === "overview"
                  ? "text-indigo-400"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Overview
              {activeSection === "overview" && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-indigo-500 rounded-full" />
              )}
            </button>
            <button
              onClick={() => setActiveSection("analytics")}
              className={`pb-3 text-sm font-bold transition-all relative ${
                activeSection === "analytics"
                  ? "text-indigo-400"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Contribution Analytics
              {activeSection === "analytics" && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-indigo-500 rounded-full" />
              )}
            </button>
          </div>

          {activeSection === "overview" && (
            <>
              {/* Languages Breakdown */}
              {report.languages.length > 0 && (
                <div className="p-6 bg-slate-900/40 border border-slate-800 rounded-xl space-y-4">
                  <h3 className="text-sm font-bold text-slate-300 flex items-center gap-2">
                    <Code className="h-4 w-4 text-indigo-400" /> Language Distribution
                  </h3>
                  
                  {/* Stacked Percentage Bar */}
                  <div className="h-3 w-full rounded-full bg-slate-950 flex overflow-hidden border border-slate-800">
                    {report.languages.map((lang, idx) => {
                      const colors = [
                        "bg-indigo-500", "bg-violet-500", "bg-purple-500", 
                        "bg-sky-500", "bg-emerald-500", "bg-pink-500"
                      ];
                      const color = colors[idx % colors.length];
                      return (
                        <div
                          key={lang.language_name}
                          style={{ width: `${lang.percentage}%` }}
                          className={`${color} h-full transition-all`}
                          title={`${lang.language_name}: ${lang.percentage}%`}
                        />
                      );
                    })}
                  </div>

                  {/* Labels Grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-4 pt-2">
                    {report.languages.map((lang, idx) => {
                      const colors = [
                        "bg-indigo-500", "bg-violet-500", "bg-purple-500", 
                        "bg-sky-500", "bg-emerald-500", "bg-pink-500"
                      ];
                      const dotColor = colors[idx % colors.length];
                      return (
                        <div key={lang.language_name} className="flex items-center gap-2 text-xs font-semibold">
                          <span className={`w-2.5 h-2.5 rounded-full ${dotColor}`} />
                          <span className="text-slate-300">{lang.language_name}</span>
                          <span className="text-slate-500 ml-auto">{lang.percentage}%</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Frameworks badging */}
              {report.frameworks.length > 0 && (
                <div className="p-6 bg-slate-900/40 border border-slate-800 rounded-xl space-y-3">
                  <h3 className="text-sm font-bold text-slate-300 flex items-center gap-2">
                    <Layers className="h-4 w-4 text-indigo-400" /> Detected Frameworks
                  </h3>
                  <div className="flex flex-wrap gap-2.5">
                    {report.frameworks.map((fw) => (
                      <span
                        key={fw.framework_name}
                        className="px-3 py-1 bg-violet-500/10 text-violet-400 font-bold text-xs border border-violet-500/20 rounded-lg shadow-sm"
                      >
                        {fw.framework_name}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Contributors & Authorship */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                
                {/* Contributors List */}
                <div className="lg:col-span-2 p-6 bg-slate-900/40 border border-slate-800 rounded-xl flex flex-col gap-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-bold text-slate-300 flex items-center gap-2">
                      <Users className="h-4 w-4 text-indigo-400" /> Contributor Breakdown
                    </h3>
                    
                    {/* Sort Toggle */}
                    <div className="flex bg-slate-950 p-0.5 rounded-md border border-slate-800 text-[10px] font-bold">
                      <button
                        onClick={() => setContribSortBy("commits")}
                        className={`px-2 py-1 rounded transition ${
                          contribSortBy === "commits" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-slate-200"
                        }`}
                      >
                        Commits
                      </button>
                      <button
                        onClick={() => setContribSortBy("percentage")}
                        className={`px-2 py-1 rounded transition ${
                          contribSortBy === "percentage" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-slate-200"
                        }`}
                      >
                        Ownership %
                      </button>
                    </div>
                  </div>

                  <div className="space-y-3.5 max-h-[300px] overflow-y-auto pr-1">
                    {sortedContributors.map((c) => (
                      <div
                        key={c.username}
                        className="p-3 bg-slate-950/30 border border-slate-800/60 rounded-xl flex items-center justify-between"
                      >
                        <div>
                          <h4 className="text-sm font-bold text-slate-200">{c.username}</h4>
                          <p className="text-[10px] text-slate-500 mt-0.5">
                            {c.commits} commits <span className="text-slate-700">•</span> <span className="text-emerald-500">+{c.additions}</span> <span className="text-rose-500">-{c.deletions}</span>
                          </p>
                        </div>

                        <div className="text-right">
                          <p className="text-sm font-bold text-indigo-400">{c.ownership_percentage}%</p>
                          <p className="text-[10px] text-slate-500">Ownership</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Quick Metrics */}
                <div className="p-6 bg-slate-900/40 border border-slate-800 rounded-xl flex flex-col justify-between">
                  <div>
                    <h3 className="text-sm font-bold text-slate-300 flex items-center gap-2 mb-4">
                      <Activity className="h-4 w-4 text-indigo-400" /> Quick Metrics
                    </h3>
                    
                    <div className="space-y-4">
                      <div className="flex justify-between items-center py-2 border-b border-slate-850 text-xs">
                        <span className="text-slate-400 font-semibold">Total Contributors</span>
                        <span className="font-bold text-indigo-300">{report.contributors.length}</span>
                      </div>
                      <div className="flex justify-between items-center py-2 border-b border-slate-850 text-xs">
                        <span className="text-slate-400 font-semibold">Primary Language</span>
                        <span className="font-bold text-indigo-300">{repository.language || "N/A"}</span>
                      </div>
                      <div className="flex justify-between items-center py-2 border-b border-slate-850 text-xs">
                        <span className="text-slate-400 font-semibold">Code Complexity</span>
                        <span className={`font-bold ${
                          report.complexity_score && report.complexity_score >= 80 ? "text-emerald-400" : "text-amber-400"
                        }`}>
                          {report.complexity_score ? `${report.complexity_score}/100` : "Scan Pending"}
                        </span>
                      </div>
                      <div className="flex justify-between items-center py-2 text-xs">
                        <span className="text-slate-400 font-semibold">Security Level</span>
                        <span className={`font-bold ${
                          report.security_score && report.security_score >= 80 ? "text-emerald-400" : "text-amber-400"
                        }`}>
                          {report.security_score ? `${report.security_score}/100` : "Scan Pending"}
                        </span>
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={() => router.push(`/repositories/${repoId}/analysis` as Route)}
                    className="mt-6 w-full py-2.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg shadow-md transition-colors"
                  >
                    Inspect Vulnerabilities & Code
                  </button>
                </div>
              </div>

              {/* Skills & Project Insights Card */}
              <div className="p-6 bg-slate-900/40 border border-slate-800 rounded-xl space-y-6">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div>
                    <h3 className="text-sm font-bold text-slate-300 flex items-center gap-2">
                      <Brain className="h-4 w-4 text-indigo-400" /> GLM Skill Extraction & Insights
                    </h3>
                    <p className="text-xs text-slate-500 mt-1 font-medium">
                      Convert code artifacts into verified developer skills and summaries powered by GLM-5.1.
                    </p>
                  </div>

                  <button
                    disabled={extracting}
                    onClick={handleExtract}
                    className="px-4 py-2 text-xs font-bold text-white bg-indigo-655 hover:bg-indigo-600 rounded-lg flex items-center gap-1.5 shadow-md shadow-indigo-600/10 transition-colors disabled:opacity-50"
                  >
                    {extracting ? <Spinner className="h-3.5 w-3.5" /> : <RefreshCw className="h-3.5 w-3.5" />}
                    {insights ? "Re-run Extraction" : "Extract Developer Profile"}
                  </button>
                </div>

                {extractError && (
                  <p className="text-[10px] text-rose-400 font-semibold flex items-center gap-1">
                    <AlertCircle className="h-3 w-3" /> {extractError}
                  </p>
                )}

                {!insights && !extracting && (
                  <div className="p-6 bg-slate-950/40 border border-slate-855 rounded-xl text-center">
                    <Brain className="h-8 w-8 text-slate-600 mx-auto mb-2" />
                    <p className="text-xs text-slate-400 font-medium">No skills extracted yet. Click the button to analyze this repository.</p>
                  </div>
                )}

                {insights && (
                  <div className="space-y-6">
                    {/* Insights Meta badges */}
                    <div className="flex flex-wrap gap-3">
                      <div className="px-3 py-1 bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 rounded-lg text-xs font-bold flex items-center gap-1.5">
                        <Tag className="h-3.5 w-3.5" /> {insights.project_type}
                      </div>
                      
                      <div className={`px-3 py-1 border rounded-lg text-xs font-bold flex items-center gap-1.5 ${
                        insights.complexity_level === "Enterprise" || insights.complexity_level === "Advanced"
                          ? "bg-rose-500/10 border-rose-500/20 text-rose-400"
                          : "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
                      }`}>
                        <Cpu className="h-3.5 w-3.5" /> {insights.complexity_level} Level
                      </div>

                      {insights.project_category.map((cat) => (
                        <div key={cat} className="px-3 py-1 bg-violet-500/10 border border-violet-500/20 text-violet-400 rounded-lg text-xs font-bold">
                          {cat}
                        </div>
                      ))}
                    </div>

                    {/* Summaries grid */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div className="p-4 bg-slate-950/40 border border-slate-850 rounded-xl space-y-2">
                        <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                          <Award className="h-3.5 w-3.5 text-indigo-400" /> Recruiter Summary
                        </h4>
                        <p className="text-xs text-slate-300 leading-relaxed font-medium">
                          {insights.project_summary}
                        </p>
                      </div>

                      <div className="p-4 bg-slate-950/40 border border-slate-850 rounded-xl space-y-2">
                        <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                          <Cpu className="h-3.5 w-3.5 text-indigo-400" /> Technical Architecture
                        </h4>
                        <p className="text-xs text-slate-300 leading-relaxed font-medium font-sans">
                          {insights.technical_summary}
                        </p>
                      </div>
                    </div>

                    {/* Extracted Skills List */}
                    {skills && skills.length > 0 && (
                      <div className="space-y-4 pt-4 border-t border-slate-850">
                        <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                          <ListChecks className="h-3.5 w-3.5 text-indigo-400" /> Verified Skills & Evidence
                        </h4>
                        
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                          {Object.entries(skillsByCategory).map(([category, catSkills]) => (
                            <div key={category} className="p-4 bg-slate-950/30 border border-slate-800/60 rounded-xl space-y-3">
                              <h5 className="text-xs font-bold text-indigo-300 border-b border-slate-850 pb-1.5">
                                {category}
                              </h5>
                              
                              <div className="flex flex-wrap gap-2">
                                {catSkills.map((s) => (
                                  <div key={s.id} className="w-full">
                                    <button
                                      onClick={() => setSelectedSkillId(selectedSkillId === s.id ? null : s.id)}
                                      className={`w-full text-left p-2 rounded-lg border text-xs flex items-center justify-between transition-colors ${
                                        selectedSkillId === s.id
                                          ? "bg-indigo-650/10 border-indigo-500/30 text-indigo-300"
                                          : "bg-slate-950/60 border-slate-800/80 text-slate-300 hover:border-slate-700"
                                      }`}
                                    >
                                      <span className="font-semibold flex items-center gap-1">
                                        <span className="text-emerald-400">✓</span> {s.skill_name}
                                      </span>
                                      <span className="font-bold text-[10px] bg-slate-900 border border-slate-800 px-1.5 py-0.5 rounded text-indigo-400">
                                        {s.confidence_score}%
                                      </span>
                                    </button>
                                    
                                    {selectedSkillId === s.id && (
                                      <div className="mt-1.5 p-2 bg-slate-950 border border-slate-800 rounded-lg text-[10px] text-slate-400 space-y-1 font-sans">
                                        <p className="font-extrabold text-slate-300 uppercase tracking-wide text-[9px] flex items-center gap-1">
                                          <ListChecks className="h-3 w-3 text-indigo-400" /> Verified Evidence:
                                        </p>
                                        {s.evidence.map((ev, index) => (
                                          <p key={index} className="pl-1">
                                            • {ev}
                                          </p>
                                        ))}
                                      </div>
                                    )}
                                  </div>
                                ))}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Deployment Verification Card */}
              <div className="p-6 bg-slate-900/40 border border-slate-800 rounded-xl space-y-6">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div>
                    <h3 className="text-sm font-bold text-slate-300 flex items-center gap-2">
                      <Globe className="h-4 w-4 text-indigo-400" /> Deployment Verification
                    </h3>
                    <p className="text-xs text-slate-500 mt-1 font-medium">
                      Auto-discover and verify the live deployment status of this codebase.
                    </p>
                  </div>

                  {deployReport && (
                    <div className={`px-3 py-1 rounded-lg text-xs font-bold border flex items-center gap-1.5 ${
                      deployReport.reachable
                        ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                        : "bg-rose-500/10 text-rose-400 border-rose-500/20"
                    }`}>
                      {deployReport.reachable ? (
                        <>
                          <CheckCircle2 className="h-3.5 w-3.5" /> Deployment Verified
                        </>
                      ) : (
                        <>
                          <AlertCircle className="h-3.5 w-3.5" /> Unreachable
                        </>
                      )}
                    </div>
                  )}
                </div>

                {/* Input & Control Buttons */}
                <div className="space-y-3">
                  <div className="flex flex-col sm:flex-row gap-3">
                    <div className="relative flex-1">
                      <Globe className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
                      <input
                        type="text"
                        placeholder="Enter deployment URL (e.g. https://my-app.vercel.app)"
                        value={deploymentUrl}
                        onChange={(e) => setDeploymentUrl(e.target.value)}
                        className="w-full pl-9 pr-4 py-2 text-xs bg-slate-950 border border-slate-800 rounded-lg text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                      />
                    </div>

                    <div className="flex gap-2">
                      <button
                        disabled={discovering}
                        onClick={handleDiscover}
                        className="px-3.5 py-2 text-xs font-semibold bg-slate-850 hover:bg-slate-800 border border-slate-700 rounded-lg text-slate-300 flex items-center gap-1.5 transition-colors disabled:opacity-50"
                      >
                        {discovering ? <Spinner className="h-3.5 w-3.5" /> : <RefreshCw className="h-3.5 w-3.5" />}
                        Discover
                      </button>

                      <button
                        disabled={verifying}
                        onClick={handleVerify}
                        className="px-4 py-2 text-xs font-bold text-white bg-indigo-650 hover:bg-indigo-600 rounded-lg flex items-center gap-1.5 shadow-md shadow-indigo-600/10 transition-colors disabled:opacity-50"
                      >
                        {verifying ? <Spinner className="h-3.5 w-3.5" /> : <ShieldCheck className="h-3.5 w-3.5" />}
                        Verify Deployment
                      </button>
                    </div>
                  </div>

                  {discoverMessage && (
                    <p className="text-[10px] text-indigo-400 font-semibold italic">
                      {discoverMessage}
                    </p>
                  )}

                  {verifyError && (
                    <p className="text-[10px] text-rose-400 font-semibold flex items-center gap-1">
                      <AlertCircle className="h-3 w-3" /> {verifyError}
                    </p>
                  )}
                </div>

                {/* Verification Detailed Report */}
                {deployReport && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 pt-6 border-t border-slate-850">
                    {/* 1. Score */}
                    <div className="p-4 bg-slate-950/40 border border-slate-855 rounded-xl space-y-1">
                      <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Deployment Score</p>
                      <p className={`text-xl font-black ${
                        deployReport.deployment_score >= 80 ? "text-emerald-400" : "text-amber-400"
                      }`}>{deployReport.deployment_score}/100</p>
                    </div>

                    {/* 2. Provider */}
                    <div className="p-4 bg-slate-950/40 border border-slate-850 rounded-xl space-y-1">
                      <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Hosting Provider</p>
                      <p className="text-xl font-extrabold text-slate-200 flex items-center gap-1.5">
                        <Server className="h-4 w-4 text-indigo-400" /> {deployReport.provider || "Unknown"}
                      </p>
                    </div>

                    {/* 3. Response Time */}
                    <div className="p-4 bg-slate-950/40 border border-slate-850 rounded-xl space-y-1">
                      <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Response Time</p>
                      <p className="text-xl font-extrabold text-slate-200 flex items-center gap-1.5">
                        <Wifi className="h-4 w-4 text-indigo-400" /> {deployReport.response_time ? `${Math.round(deployReport.response_time)}ms` : "N/A"}
                      </p>
                    </div>

                    {/* 4. SSL Status */}
                    <div className="p-4 bg-slate-950/40 border border-slate-850 rounded-xl space-y-1">
                      <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">SSL Certificate</p>
                      <p className={`text-sm font-extrabold flex items-center gap-1.5 mt-1.5 ${
                        deployReport.ssl_enabled ? "text-emerald-400" : "text-rose-400"
                      }`}>
                        <Lock className="h-4 w-4 text-indigo-400" />
                        {deployReport.ssl_enabled
                          ? deployReport.ssl_expiry_days
                            ? `Valid (${deployReport.ssl_expiry_days}d left)`
                            : "Valid"
                          : "Invalid/Inactive"}
                      </p>
                    </div>

                    {/* 5. Headers Score */}
                    <div className="p-4 bg-slate-950/40 border border-slate-855 rounded-xl space-y-1">
                      <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Security Headers</p>
                      <p className="text-base font-extrabold text-slate-200">
                        {deployReport.security_headers_score}/100
                      </p>
                    </div>

                    {/* 6. Asset Health */}
                    <div className="p-4 bg-slate-950/40 border border-slate-855 rounded-xl space-y-1">
                      <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Asset Health</p>
                      <p className="text-base font-extrabold text-slate-200">
                        {deployReport.asset_health_score}/100
                      </p>
                    </div>

                    {/* 7. Link Health */}
                    <div className="p-4 bg-slate-950/40 border border-slate-855 rounded-xl space-y-1">
                      <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Link validation</p>
                      <p className="text-base font-extrabold text-slate-200">
                        {deployReport.internal_link_score}/100
                      </p>
                    </div>

                    {/* 8. Verified Date */}
                    <div className="p-4 bg-slate-950/40 border border-slate-855 rounded-xl space-y-1">
                      <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Last Checked</p>
                      <p className="text-xs font-semibold text-slate-400 mt-1">
                        {new Date(deployReport.created_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                )}
              </div>

              {/* Dependencies List */}
              <div className="p-6 bg-slate-900/40 border border-slate-800 rounded-xl space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <h3 className="text-sm font-bold text-slate-300 flex items-center gap-2">
                    <Layers className="h-4 w-4 text-indigo-400" /> Project Dependencies ({report.dependencies.length})
                  </h3>
                  
                  {/* Search Dependency */}
                  <div className="relative w-full sm:w-64">
                    <Search className="absolute left-2.5 top-2 h-3.5 w-3.5 text-slate-400" />
                    <input
                      type="text"
                      placeholder="Search dependency..."
                      value={depSearchQuery}
                      onChange={(e) => setDepSearchQuery(e.target.value)}
                      className="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-950 border border-slate-800 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                </div>

                {report.dependencies.length === 0 ? (
                  <p className="text-xs text-slate-450 italic py-4 text-center">
                    No manifest file (package.json, requirements.txt, go.mod, Cargo.toml) detected or parsed.
                  </p>
                ) : filteredDeps.length === 0 ? (
                  <p className="text-xs text-slate-450 italic py-4 text-center">
                    No dependencies matching search.
                  </p>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 max-h-[400px] overflow-y-auto pr-1">
                    {filteredDeps.map((dep) => (
                      <div
                        key={dep.dependency_name}
                        className="p-3 bg-slate-950/40 border border-slate-800/80 rounded-lg flex items-center justify-between text-xs"
                      >
                        <span className="font-semibold text-slate-300 truncate max-w-[150px]" title={dep.dependency_name}>
                          {dep.dependency_name}
                        </span>
                        <span className="font-mono text-indigo-400 px-1.5 py-0.5 rounded bg-indigo-500/5 border border-indigo-500/10">
                          {dep.version}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}

          {activeSection === "analytics" && (
            <div className="space-y-8 animate-fade-in">
              {/* Action Banner */}
              <div className="p-6 bg-slate-900/40 border border-slate-800 rounded-xl flex flex-col md:flex-row md:items-center justify-between gap-6">
                <div className="space-y-1">
                  <h3 className="text-base font-bold text-slate-200 flex items-center gap-2">
                    <ShieldCheck className="h-5 w-5 text-indigo-400" /> Contribution Verification Dashboard
                  </h3>
                  <p className="text-xs text-slate-400 font-medium">
                    Verify developer ownership, code contributions, activity scores, and module ownership using git telemetry.
                  </p>
                </div>

                <button
                  disabled={analyzing}
                  onClick={handleAnalyzeContributions}
                  className="px-5 py-2.5 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg flex items-center justify-center gap-2 shadow-md shadow-indigo-600/10 transition-colors disabled:opacity-50 min-w-[180px]"
                >
                  {analyzing ? (
                    <>
                      <Spinner className="h-3.5 w-3.5" />
                      Analyzing Git Logs...
                    </>
                  ) : (
                    <>
                      <RefreshCw className="h-3.5 w-3.5" />
                      {contribReport ? "Re-run Verification" : "Verify Repository"}
                    </>
                  )}
                </button>
              </div>

              {analysisError && (
                <div className="p-4 bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-xl text-xs flex items-center gap-2">
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  <span>{analysisError}</span>
                </div>
              )}

              {!contribReport && !analyzing && (
                <div className="p-12 bg-slate-900/20 border border-slate-850 rounded-xl text-center flex flex-col items-center justify-center space-y-4">
                  <div className="p-4 bg-slate-950 border border-slate-800 rounded-2xl text-slate-500">
                    <Users className="h-10 w-10 text-indigo-500/60" />
                  </div>
                  <div className="max-w-sm space-y-2">
                    <h4 className="text-sm font-bold text-slate-200">No Contribution Verification Run Yet</h4>
                    <p className="text-xs text-slate-500 font-medium">
                      Run the verification engine to clone the repository, calculate lines added/deleted, file ownership, and generate AI insights.
                    </p>
                  </div>
                  <button
                    onClick={handleAnalyzeContributions}
                    className="px-4 py-2 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg shadow-md transition-colors"
                  >
                    Verify Contributions
                  </button>
                </div>
              )}

              {contribReport && (
                <>
                  {/* Verification Summary & Metrics */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
                    {/* Primary Contributor */}
                    <div className="p-5 bg-slate-900/40 border border-slate-800 rounded-xl flex flex-col justify-between space-y-3">
                      <div>
                        <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Lead Developer</span>
                        <span className="text-lg font-black text-slate-100 block mt-1 truncate">
                          {contribReport.primary_contributor}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-slate-400">
                        <div className="w-6 h-6 rounded-full bg-indigo-955 border border-indigo-850 flex items-center justify-center font-bold text-indigo-400 text-[10px]">
                          {contribReport.primary_contributor.substring(0, 2).toUpperCase()}
                        </div>
                        <span className="font-semibold">Primary Contributor</span>
                      </div>
                    </div>

                    {/* Code Ownership Score */}
                    <div className="p-5 bg-slate-900/40 border border-slate-800 rounded-xl flex flex-col justify-between space-y-3">
                      <div>
                        <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Code Ownership</span>
                        <span className="text-2xl font-black text-indigo-400 block mt-1">
                          {contribReport.ownership_score}%
                        </span>
                      </div>
                      <div className="w-full bg-slate-950 h-1.5 rounded-full overflow-hidden border border-slate-850">
                        <div 
                          className="h-full bg-indigo-500 rounded-full" 
                          style={{ width: `${contribReport.ownership_score}%` }} 
                        />
                      </div>
                    </div>

                    {/* Activity Index */}
                    <div className="p-5 bg-slate-900/40 border border-slate-800 rounded-xl flex flex-col justify-between space-y-3">
                      <div>
                        <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Activity Index</span>
                        <span className="text-2xl font-black text-indigo-400 block mt-1">
                          {contribReport.activity_score}/100
                        </span>
                      </div>
                      <div className="w-full bg-slate-950 h-1.5 rounded-full overflow-hidden border border-slate-850">
                        <div 
                          className="h-full bg-indigo-500 rounded-full" 
                          style={{ width: `${contribReport.activity_score}%` }} 
                        />
                      </div>
                    </div>

                    {/* Verification Confidence */}
                    <div className="p-5 bg-slate-900/40 border border-slate-800 rounded-xl flex flex-col justify-between space-y-3">
                      <div>
                        <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Verification Confidence</span>
                        <span className={`text-2xl font-black block mt-1 ${
                          contribReport.confidence >= 80 ? "text-emerald-400" : "text-amber-400"
                        }`}>
                          {contribReport.confidence}%
                        </span>
                      </div>
                      <span className="text-[10px] text-slate-500 font-semibold block">
                        Confidence score based on Git telemetry & path analysis.
                      </span>
                    </div>
                  </div>

                  {/* AI Contribution Summary */}
                  <div className="p-6 bg-slate-900/40 border border-slate-800 rounded-xl space-y-3">
                    <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                      <Brain className="h-4 w-4 text-indigo-400" /> GLM Contribution Analysis
                    </h4>
                    <p className="text-xs text-slate-300 leading-relaxed font-semibold">
                      {contribReport.summary}
                    </p>
                  </div>

                  {/* Charts & Visualization Section */}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Pie Chart of Code Ownership */}
                    <div className="p-6 bg-slate-900/40 border border-slate-800 rounded-xl space-y-4">
                      <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                        <TrendingUp className="h-4 w-4 text-indigo-400" /> Code Ownership Share
                      </h4>
                      <div className="h-64 flex items-center justify-center">
                        {isClient && contributorsList && contributorsList.length > 0 ? (
                          <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                              <Pie
                                data={contributorsList}
                                dataKey="ownership_percentage"
                                nameKey="username"
                                cx="50%"
                                cy="50%"
                                outerRadius={80}
                                fill="#8884d8"
                                label={(props: { name?: string; value?: number }) => 
                                  `${props.name ?? ""} (${props.value ?? 0}%)`
                                }
                              >
                                {contributorsList.map((entry, index) => (
                                  <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                                ))}
                              </Pie>
                              <ChartTooltip 
                                contentStyle={{ backgroundColor: "#0f172a", borderColor: "#1e293b", color: "#f8fafc" }}
                                itemStyle={{ color: "#a5b4fc" }}
                              />
                            </PieChart>
                          </ResponsiveContainer>
                        ) : (
                          <div className="text-xs text-slate-500 italic">No contributor metrics data available.</div>
                        )}
                      </div>
                    </div>

                    {/* Bar Chart of Commits and Activity */}
                    <div className="p-6 bg-slate-900/40 border border-slate-800 rounded-xl space-y-4">
                      <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                        <BarChart2 className="h-4 w-4 text-indigo-400" /> Contributor Commit Volumes
                      </h4>
                      <div className="h-64">
                        {isClient && contributorsList && contributorsList.length > 0 ? (
                          <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={contributorsList} margin={{ top: 20, right: 20, left: -10, bottom: 0 }}>
                              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                              <XAxis dataKey="username" stroke="#94a3b8" fontSize={10} tickLine={false} />
                              <YAxis stroke="#94a3b8" fontSize={10} tickLine={false} />
                              <ChartTooltip
                                contentStyle={{ backgroundColor: "#0f172a", borderColor: "#1e293b", color: "#f8fafc" }}
                                itemStyle={{ color: "#a5b4fc" }}
                              />
                              <Bar dataKey="total_commits" name="Commits" fill="#6366f1" radius={[4, 4, 0, 0]} />
                            </BarChart>
                          </ResponsiveContainer>
                        ) : (
                          <div className="text-xs text-slate-500 italic">No contributor commits data available.</div>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Module Ownership Matrix */}
                  <div className="p-6 bg-slate-900/40 border border-slate-800 rounded-xl space-y-4">
                    <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                      <Layers className="h-4 w-4 text-indigo-400" /> Module Ownership Breakdown
                    </h4>
                    
                    {!ownershipBreakdown || ownershipBreakdown.length === 0 ? (
                      <p className="text-xs text-slate-500 italic py-4 text-center">No module ownership matrix available.</p>
                    ) : (
                      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                        {Object.entries(
                          ownershipBreakdown.reduce((acc, curr) => {
                            const mName = curr.module_name;
                            if (!acc[mName]) acc[mName] = [];
                            acc[mName].push(curr);
                            return acc;
                          }, {} as Record<string, ModuleOwnership[]>)
                        ).map(([modName, items]) => (
                          <div key={modName} className="p-4 bg-slate-950/40 border border-slate-800 rounded-xl space-y-3">
                            <h5 className="text-xs font-bold text-indigo-300 border-b border-slate-850 pb-2">
                              {modName}
                            </h5>
                            <div className="space-y-2">
                              {items.map((item) => (
                                <div key={item.id} className="flex justify-between items-center text-xs">
                                  <span className="text-slate-300 font-medium">{item.username}</span>
                                  <div className="flex items-center gap-2">
                                    <div className="w-16 bg-slate-900 h-1.5 rounded-full overflow-hidden border border-slate-800">
                                      <div 
                                        className="h-full bg-violet-500" 
                                        style={{ width: `${item.ownership_percentage}%` }} 
                                      />
                                    </div>
                                    <span className="font-bold text-slate-400 text-[10px] min-w-[32px] text-right">
                                      {Math.round(item.ownership_percentage)}%
                                    </span>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Detailed Verified Contributor Leaderboard */}
                  <div className="p-6 bg-slate-900/40 border border-slate-800 rounded-xl space-y-4">
                    <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                      <Users className="h-4 w-4 text-indigo-400" /> Verified Contributor Telemetry
                    </h4>
                    
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs border-collapse">
                        <thead>
                          <tr className="border-b border-slate-800 text-slate-500 font-bold">
                            <th className="py-3 px-4">Contributor</th>
                            <th className="py-3 px-4">Commits</th>
                            <th className="py-3 px-4">Lines Added</th>
                            <th className="py-3 px-4">Lines Deleted</th>
                            <th className="py-3 px-4">Activity Score</th>
                            <th className="py-3 px-4 text-right">Ownership Share</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-850">
                          {contributorsList?.map((c) => (
                            <tr key={c.id} className="hover:bg-slate-900/20 transition-colors">
                              <td className="py-3.5 px-4 font-bold text-slate-200 flex items-center gap-2.5">
                                {c.avatar_url ? (
                                  <img 
                                    src={c.avatar_url} 
                                    alt={c.username} 
                                    className="w-6 h-6 rounded-full border border-slate-800" 
                                  />
                                ) : (
                                  <div className="w-6 h-6 rounded-full bg-indigo-950 border border-indigo-850 flex items-center justify-center font-bold text-[10px] text-indigo-400">
                                    {c.username.substring(0, 2).toUpperCase()}
                                  </div>
                                )}
                                <span>{c.username}</span>
                              </td>
                              <td className="py-3.5 px-4 text-slate-300 font-semibold">{c.total_commits}</td>
                              <td className="py-3.5 px-4 text-emerald-400 font-semibold">+{c.lines_added}</td>
                              <td className="py-3.5 px-4 text-rose-400 font-semibold">-{c.lines_deleted}</td>
                              <td className="py-3.5 px-4">
                                <span className="px-2 py-0.5 bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 rounded-md font-bold text-[10px]">
                                  {c.activity_score}/100
                                </span>
                              </td>
                              <td className="py-3.5 px-4 text-right font-extrabold text-indigo-400">
                                {c.ownership_percentage}%
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </ProtectedRoute>
  );
}

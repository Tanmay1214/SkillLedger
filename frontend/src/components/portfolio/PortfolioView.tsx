"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import type { PortfolioResponse, PortfolioProject, SkillGroup } from "@/types/portfolio";

// ── Score ring helpers ─────────────────────────────────────────────────────────

function ScoreRing({ value, label, color }: { value: number; label: string; color: string }) {
  const r = 30;
  const circ = 2 * Math.PI * r;
  const offset = circ - (value / 100) * circ;

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative w-[76px] h-[76px]">
        <svg className="w-full h-full -rotate-90" viewBox="0 0 76 76">
          <circle cx="38" cy="38" r={r} fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="7" />
          <circle
            cx="38"
            cy="38"
            r={r}
            fill="none"
            stroke={color}
            strokeWidth="7"
            strokeLinecap="round"
            strokeDasharray={circ}
            strokeDashoffset={offset}
            style={{ transition: "stroke-dashoffset 1s cubic-bezier(.4,0,.2,1)" }}
          />
        </svg>
        <span className="absolute inset-0 flex items-center justify-center text-base font-bold text-white">
          {value}
        </span>
      </div>
      <span className="text-[11px] text-white/40 uppercase tracking-wider font-medium">{label}</span>
    </div>
  );
}

// ── Badge ──────────────────────────────────────────────────────────────────────

function Badge({ text, variant = "default" }: { text: string; variant?: "default" | "green" | "blue" | "purple" | "amber" }) {
  const colors: Record<string, string> = {
    default: "bg-white/5 text-white/60 border-white/10",
    green: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    blue: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    purple: "bg-violet-500/10 text-violet-400 border-violet-500/20",
    amber: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  };
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-medium border ${colors[variant]}`}>
      {text}
    </span>
  );
}

// ── Skill confidence bar ───────────────────────────────────────────────────────

function SkillBar({ name, score }: { name: string; score: number }) {
  return (
    <div className="flex items-center gap-3 group">
      <span className="text-sm text-white/70 w-36 truncate group-hover:text-white transition-colors">{name}</span>
      <div className="flex-1 h-1.5 rounded-full bg-white/5 overflow-hidden">
        <div
          className="h-full rounded-full bg-gradient-to-r from-violet-500 to-indigo-400"
          style={{ width: `${score}%`, transition: "width 1s cubic-bezier(.4,0,.2,1)" }}
        />
      </div>
      <span className="text-xs text-white/30 w-8 text-right">{score}</span>
    </div>
  );
}

// ── Score pill ─────────────────────────────────────────────────────────────────

function ScorePill({ label, value, color }: { label: string; value: number | null; color: string }) {
  if (value === null) return null;
  return (
    <div className="flex items-center gap-1.5">
      <div className="w-1.5 h-1.5 rounded-full" style={{ background: color }} />
      <span className="text-xs text-white/40">{label}</span>
      <span className="text-xs font-semibold text-white/80">{value}</span>
    </div>
  );
}

// ── Project card ───────────────────────────────────────────────────────────────

function ProjectCard({ project }: { project: PortfolioProject }) {
  const [expanded, setExpanded] = useState(false);

  const complexityColor = (level: string | null) => {
    if (!level) return "default";
    const l = level.toLowerCase();
    if (l.includes("high") || l.includes("complex")) return "amber";
    if (l.includes("medium") || l.includes("moderate")) return "blue";
    return "green";
  };

  return (
    <div className="group relative rounded-2xl border border-white/[0.07] bg-white/[0.02] hover:bg-white/[0.04] hover:border-white/[0.12] transition-all duration-300 overflow-hidden">
      {/* Top gradient accent based on build score */}
      <div
        className="absolute top-0 left-0 right-0 h-px"
        style={{
          background: project.build_score
            ? `linear-gradient(90deg, transparent, hsl(${260 + project.build_score * 0.8}, 70%, 65%), transparent)`
            : "rgba(255,255,255,0.05)",
        }}
      />

      <div className="p-5">
        {/* Header row */}
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <h3 className="font-semibold text-white text-[15px] truncate">{project.name}</h3>
              {project.project_type && (
                <Badge text={project.project_type} variant="purple" />
              )}
              {project.complexity_level && (
                <Badge text={project.complexity_level} variant={complexityColor(project.complexity_level)} />
              )}
            </div>
            {project.language && (
              <span className="text-xs text-white/40">{project.language}</span>
            )}
          </div>

          {/* Scores */}
          <div className="flex gap-3 shrink-0">
            {project.build_score !== null && (
              <ScoreRing value={project.build_score} label="Build" color="#818cf8" />
            )}
            {project.proof_score !== null && (
              <ScoreRing value={project.proof_score} label="Proof" color="#34d399" />
            )}
          </div>
        </div>

        {/* Summary */}
        {project.project_summary && (
          <p className="text-sm text-white/50 leading-relaxed line-clamp-2 mb-3">
            {project.project_summary}
          </p>
        )}

        {/* Sub-scores row */}
        <div className="flex flex-wrap gap-3 mb-3">
          <ScorePill label="Complexity" value={project.complexity_score} color="#a78bfa" />
          <ScorePill label="Security" value={project.security_score} color="#f59e0b" />
          <ScorePill label="Docs" value={project.documentation_score} color="#60a5fa" />
          <ScorePill label="Contribution" value={project.contribution_percentage !== null ? Math.round(project.contribution_percentage) : null} color="#34d399" />
          <ScorePill label="Deployment" value={project.deployment_score} color="#f472b6" />
        </div>

        {/* Tags row */}
        <div className="flex flex-wrap gap-1.5 mb-3">
          {project.frameworks.slice(0, 4).map((fw) => (
            <Badge key={fw} text={fw} />
          ))}
          {project.project_categories.slice(0, 2).map((cat) => (
            <Badge key={cat} text={cat} variant="blue" />
          ))}
          {project.deployment_reachable === true && (
            <Badge text="✓ Live" variant="green" />
          )}
          {project.stars > 0 && (
            <Badge text={`★ ${project.stars}`} variant="amber" />
          )}
        </div>

        {/* Expand toggle */}
        {(project.technical_summary || project.contribution_summary) && (
          <button
            onClick={() => setExpanded((e) => !e)}
            className="text-xs text-violet-400 hover:text-violet-300 transition-colors font-medium"
          >
            {expanded ? "Hide details ↑" : "Show details ↓"}
          </button>
        )}

        {expanded && (
          <div className="mt-3 space-y-3 pt-3 border-t border-white/[0.05]">
            {project.technical_summary && (
              <div>
                <p className="text-[11px] uppercase tracking-wider text-white/30 mb-1">Technical Summary</p>
                <p className="text-sm text-white/60 leading-relaxed">{project.technical_summary}</p>
              </div>
            )}
            {project.contribution_summary && (
              <div>
                <p className="text-[11px] uppercase tracking-wider text-white/30 mb-1">Contribution</p>
                <p className="text-sm text-white/60 leading-relaxed">{project.contribution_summary}</p>
              </div>
            )}
          </div>
        )}

        {/* Footer links */}
        <div className="flex items-center gap-3 mt-4 pt-3 border-t border-white/[0.05]">
          <a
            href={project.repo_url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 text-xs text-white/40 hover:text-white/80 transition-colors"
          >
            <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z" />
            </svg>
            GitHub
          </a>
          {project.deployment_url && (
            <a
              href={project.deployment_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 text-xs text-white/40 hover:text-white/80 transition-colors"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
              {project.provider ?? "Live"}
              {project.deployment_reachable === false && (
                <span className="text-red-400"> ✗</span>
              )}
            </a>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Stats card ─────────────────────────────────────────────────────────────────

function StatCard({ label, value, sublabel, icon }: { label: string; value: string | number; sublabel?: string; icon: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-white/[0.07] bg-white/[0.02] p-5 flex items-center gap-4">
      <div className="w-10 h-10 rounded-xl bg-violet-500/10 flex items-center justify-center text-violet-400 shrink-0">
        {icon}
      </div>
      <div>
        <p className="text-2xl font-bold text-white">{value}</p>
        <p className="text-xs text-white/40">{label}</p>
        {sublabel && <p className="text-[10px] text-white/25 mt-0.5">{sublabel}</p>}
      </div>
    </div>
  );
}

// ── Filter tab ─────────────────────────────────────────────────────────────────

function FilterTab({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
        active
          ? "bg-violet-600 text-white shadow-[0_0_20px_rgba(139,92,246,0.3)]"
          : "text-white/40 hover:text-white/70 hover:bg-white/5"
      }`}
    >
      {children}
    </button>
  );
}

// ── Main view ──────────────────────────────────────────────────────────────────

export default function PortfolioView({ portfolio }: { portfolio: PortfolioResponse }) {
  const { header, verification_summary, skill_groups, projects } = portfolio;

  const [activeFilter, setActiveFilter] = useState<string>("all");
  const [activeSkillCat, setActiveSkillCat] = useState<string>(skill_groups[0]?.category ?? "");

  // Collect all project types for filter tabs
  const projectTypes = useMemo(() => {
    const types = new Set<string>();
    projects.forEach((p) => { if (p.project_type) types.add(p.project_type); });
    return Array.from(types);
  }, [projects]);

  const filteredProjects = useMemo(() => {
    if (activeFilter === "all") return projects;
    if (activeFilter === "deployed") return projects.filter((p) => p.deployment_reachable === true);
    return projects.filter((p) => p.project_type === activeFilter);
  }, [projects, activeFilter]);

  const activeGroup: SkillGroup | undefined = skill_groups.find((g) => g.category === activeSkillCat);

  return (
    <div className="min-h-screen bg-[#07070d] text-white font-sans">
      {/* Background glow */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[500px] bg-violet-700/10 blur-[120px] rounded-full" />
        <div className="absolute bottom-0 right-0 w-[600px] h-[400px] bg-indigo-700/5 blur-[100px] rounded-full" />
      </div>

      <div className="relative z-10">
        {/* ── Hero ───────────────────────────────────────────────────────────── */}
        <section className="border-b border-white/[0.05] bg-gradient-to-b from-[#0e0e1c]/80 to-transparent py-16 px-4">
          <div className="max-w-5xl mx-auto flex flex-col items-center text-center gap-5">
            {/* Avatar */}
            {header.avatar_url ? (
              <div className="relative">
                <div className="absolute inset-0 rounded-full bg-gradient-to-br from-violet-500 to-indigo-600 blur-md opacity-50 scale-110" />
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={header.avatar_url}
                  alt={header.username}
                  className="relative w-24 h-24 rounded-full ring-2 ring-white/10 object-cover"
                />
              </div>
            ) : (
              <div className="w-24 h-24 rounded-full bg-gradient-to-br from-violet-600 to-indigo-500 flex items-center justify-center text-3xl font-bold">
                {header.username[0]?.toUpperCase()}
              </div>
            )}

            {/* Name & username */}
            <div>
              <h1 className="text-3xl sm:text-4xl font-bold text-white mb-1">
                {header.name ?? header.username}
              </h1>
              <a
                href={header.github_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 text-white/40 hover:text-white/70 transition-colors text-sm"
              >
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z" />
                </svg>
                @{header.username}
              </a>
            </div>

            {/* Average scores */}
            <div className="flex gap-8 mt-2">
              <ScoreRing value={Math.round(header.avg_build_score)} label="Avg Build" color="#818cf8" />
              <ScoreRing value={Math.round(header.avg_proof_score)} label="Avg Proof" color="#34d399" />
            </div>

            {/* Verified badge */}
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm font-medium">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Verified by ProofForge
            </div>
          </div>
        </section>

        {/* ── Stats ──────────────────────────────────────────────────────────── */}
        <section className="max-w-5xl mx-auto px-4 py-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard
              label="Repositories"
              value={header.repositories_verified}
              icon={<svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" /></svg>}
            />
            <StatCard
              label="Deployments Verified"
              value={verification_summary.deployments_verified}
              icon={<svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 12h14M12 5l7 7-7 7" /></svg>}
            />
            <StatCard
              label="Verified Skills"
              value={verification_summary.verified_skills_count}
              icon={<svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>}
            />
            <StatCard
              label="Primary Contributor"
              value={verification_summary.primary_contributor_projects}
              sublabel="projects"
              icon={<svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>}
            />
          </div>
        </section>

        {/* ── Skills ─────────────────────────────────────────────────────────── */}
        {skill_groups.length > 0 && (
          <section className="max-w-5xl mx-auto px-4 pb-10">
            <h2 className="text-lg font-semibold text-white mb-4">Verified Skills</h2>
            <div className="rounded-2xl border border-white/[0.07] bg-white/[0.02] overflow-hidden">
              {/* Category tabs */}
              <div className="flex gap-1 p-3 border-b border-white/[0.05] flex-wrap">
                {skill_groups.map((g) => (
                  <FilterTab
                    key={g.category}
                    active={activeSkillCat === g.category}
                    onClick={() => setActiveSkillCat(g.category)}
                  >
                    {g.category}
                    <span className="ml-1.5 text-[10px] opacity-60">({g.skills.length})</span>
                  </FilterTab>
                ))}
              </div>

              {/* Skill bars */}
              {activeGroup && (
                <div className="p-5 grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {activeGroup.skills.map((sk) => (
                    <SkillBar key={`${sk.skill_name}-${sk.category}`} name={sk.skill_name} score={sk.confidence_score} />
                  ))}
                </div>
              )}
            </div>
          </section>
        )}

        {/* ── Projects ───────────────────────────────────────────────────────── */}
        <section className="max-w-5xl mx-auto px-4 pb-16">
          <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
            <h2 className="text-lg font-semibold text-white">
              Projects
              <span className="ml-2 text-sm text-white/30 font-normal">{filteredProjects.length}</span>
            </h2>
            {/* Filters */}
            <div className="flex flex-wrap gap-1">
              <FilterTab active={activeFilter === "all"} onClick={() => setActiveFilter("all")}>All</FilterTab>
              <FilterTab active={activeFilter === "deployed"} onClick={() => setActiveFilter("deployed")}>🚀 Deployed</FilterTab>
              {projectTypes.map((t) => (
                <FilterTab key={t} active={activeFilter === t} onClick={() => setActiveFilter(t)}>
                  {t}
                </FilterTab>
              ))}
            </div>
          </div>

          {filteredProjects.length === 0 ? (
            <div className="rounded-2xl border border-white/[0.07] bg-white/[0.02] p-12 text-center">
              <p className="text-white/30">No projects match this filter.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {filteredProjects.map((project) => (
                <ProjectCard key={project.id} project={project} />
              ))}
            </div>
          )}
        </section>

        {/* ── Footer ─────────────────────────────────────────────────────────── */}
        <footer className="border-t border-white/[0.05] py-8 px-4 text-center">
          <p className="text-xs text-white/20">
            Powered by{" "}
            <Link href="/" className="text-violet-400/70 hover:text-violet-400 transition-colors">
              ProofForge
            </Link>{" "}
            · All scores are computed from real GitHub data
          </p>
        </footer>
      </div>
    </div>
  );
}

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.repository import Repository, RepositoryAnalysis, Skill, ProjectInsight
from app.services.skill_preprocessor import SkillExtractionPreprocessor
from app.services.glm_prompt_builder import GLMPromptBuilder
from app.services.glm_client import GLMClient

logger = logging.getLogger(__name__)


class SkillExtractionService:
    """Service to analyze repositories and extract developer skills and recruiter insights using GLM or heuristics."""

    @staticmethod
    def _run_heuristic_extraction(data: Dict[str, Any]) -> Dict[str, Any]:
        """Fallbacks to deterministic heuristics if GLM-5.1 is not configured or fails.

        Ensures offline capability and zero hallucinations.
        """
        logger.info("Executing heuristic skills extraction (fallback mode).")
        
        languages = data.get("languages", [])
        frameworks = data.get("frameworks", [])
        dependencies = [d.split(" ")[0] for d in data.get("dependencies", [])]  # Clean version details
        
        # 1. Project Type
        project_type = "Web Application"
        if "Android SDK" in frameworks or "Kotlin" in languages or "Swift" in languages:
            project_type = "Mobile Application"
        elif "FastAPI" in frameworks or "Flask" in frameworks or "Gin" in frameworks:
            project_type = "API Service"
        elif "React" in frameworks or "Next.js" in frameworks or "Vue" in frameworks:
            project_type = "Frontend Web Application"
        elif "Go" in languages or "Rust" in languages:
            project_type = "CLI Tool"
            
        # 2. Project Category
        categories = []
        if project_type == "Mobile Application":
            categories.append("Mobile Development")
        if any(l in ["Python", "Go", "Rust", "Java"] for l in languages):
            categories.append("Backend Development")
        if any(l in ["TypeScript", "JavaScript", "HTML", "CSS"] for l in languages):
            categories.append("Frontend Development")
            
        if len(categories) > 1:
            categories = ["Full Stack Development"]
        elif not categories:
            categories = ["Backend Development"]

        # 3. Complexity Level
        complexity_score = data.get("complexity_score", 0)
        total_commits = data.get("commit_statistics", {}).get("total_commits", 0)
        
        if complexity_score > 75 or total_commits > 120:
            complexity_level = "Enterprise"
        elif complexity_score > 50 or total_commits > 50:
            complexity_level = "Advanced"
        elif complexity_score > 20 or total_commits > 10:
            complexity_level = "Intermediate"
        else:
            complexity_level = "Beginner"

        # 4. Extract Skills with Evidence
        skills = []
        
        # Languages
        for lang in languages:
            skills.append({
                "name": lang,
                "category": "Programming Languages",
                "confidence": 95,
                "evidence": [f"{lang} source code detected in repository analysis."]
            })
            
        # Frameworks
        for fw in frameworks:
            skills.append({
                "name": fw,
                "category": "Frameworks",
                "confidence": 98,
                "evidence": [f"{fw} framework imports identified in source codebase."]
            })
            
        # Dependencies / Databases / Cloud Platforms detection
        db_keywords = {"postgresql": "PostgreSQL", "postgres": "PostgreSQL", "sqlite": "SQLite", "mysql": "MySQL", "redis": "Redis", "mongodb": "MongoDB"}
        cloud_keywords = {"aws": "AWS", "firebase": "Firebase", "supabase": "Supabase", "docker": "Docker", "kubernetes": "Kubernetes"}
        
        for dep in dependencies:
            dep_lower = dep.lower()
            
            # DB Detection
            matched_db = next((v for k, v in db_keywords.items() if k in dep_lower), None)
            if matched_db:
                skills.append({
                    "name": matched_db,
                    "category": "Databases",
                    "confidence": 90,
                    "evidence": [f"Database library '{dep}' imported in dependencies."]
                })
            
            # Cloud/DevOps Detection
            matched_cloud = next((v for k, v in cloud_keywords.items() if k in dep_lower), None)
            if matched_cloud:
                skills.append({
                    "name": matched_cloud,
                    "category": "Cloud Platforms",
                    "confidence": 92,
                    "evidence": [f"Cloud/Deployment module '{dep}' declared in manifest."]
                })
                
            # Fallback dependency skill
            if not matched_db and not matched_cloud:
                skills.append({
                    "name": dep,
                    "category": "Software Engineering",
                    "confidence": 85,
                    "evidence": [f"External package '{dep}' listed in dependency registry."]
                })

        # Add REST API skill if backend frameworks detected
        if any(f in frameworks for f in ["FastAPI", "Flask", "Gin", "Django"]):
            skills.append({
                "name": "REST API Development",
                "category": "Backend Development",
                "confidence": 92,
                "evidence": ["Web frameworks suitable for REST APIs detected in codebase."]
            })

        # Version Control skill
        if total_commits > 0:
            skills.append({
                "name": "Version Control (Git)",
                "category": "DevOps",
                "confidence": 90,
                "evidence": [f"Repository tracking records {total_commits} commits."]
            })

        # Documentation skill
        doc_score = data.get("documentation_score", 0)
        if doc_score > 60:
            skills.append({
                "name": "Technical Writing",
                "category": "Software Engineering",
                "confidence": doc_score,
                "evidence": [f"README repository documentation scored {doc_score}/100 in audit."]
            })

        # 5. Summaries
        lang_str = ", ".join(languages) if languages else "N/A"
        fw_str = ", ".join(frameworks) if frameworks else "N/A"
        dep_str = ", ".join(dependencies[:4]) if dependencies else "None"
        
        project_summary = (
            f"This project is a {project_type} built using {lang_str}. "
            f"It represents engineering patterns for {', '.join(categories)}, utilizing frameworks like {fw_str} "
            f"with integrations including {dep_str}."
        )
        
        technical_summary = (
            f"Architecture implements {lang_str} programming stacks. "
            f"Integrated frameworks: {fw_str}. Third-party dependencies: {dep_str}. "
            f"Code metrics record complexity of {complexity_score}/100 and a documentation index of {doc_score}/100."
        )

        return {
            "project_type": project_type,
            "project_category": categories,
            "complexity_level": complexity_level,
            "skills": skills,
            "project_summary": project_summary,
            "technical_summary": technical_summary,
        }

    @classmethod
    async def extract_and_save_skills(
        cls,
        db: AsyncSession,
        repository_id: int,
    ) -> Optional[ProjectInsight]:
        """Gathers intelligence, runs GLM skill analysis or heuristic fallback,

        saves the results to SQLite/PostgreSQL, and returns the insight object.
        """
        logger.info(f"Triggering skill extraction process for repository_id={repository_id}")
        
        # 1. Fetch Repository
        repo_stmt = select(Repository).where(Repository.id == repository_id)
        repo_res = await db.execute(repo_stmt)
        repository = repo_res.scalars().first()
        if not repository:
            logger.error(f"Repository {repository_id} not found in database.")
            return None
            
        # 2. Get latest completed analysis
        analysis_stmt = (
            select(RepositoryAnalysis)
            .where(RepositoryAnalysis.repository_id == repository_id)
            .where(RepositoryAnalysis.analysis_status == "completed")
            .order_by(RepositoryAnalysis.created_at.desc())
        )
        analysis_res = await db.execute(analysis_stmt)
        analysis = analysis_res.scalars().first()
        if not analysis:
            logger.warning(f"No completed RepositoryAnalysis found for repository {repository_id}. Skipping extraction.")
            return None

        # 3. Preprocess repository to make clean compact input context
        preprocessed_data = await SkillExtractionPreprocessor.preprocess_repository(db, repository, analysis)

        # 4. Check API configurations
        extracted_data = None
        if settings.glm_api_key:
            system_prompt = GLMPromptBuilder.build_system_prompt()
            user_prompt = GLMPromptBuilder.build_user_prompt(preprocessed_data)
            
            client = GLMClient(settings.glm_api_key)
            extracted_data = await client.extract_project_metadata(system_prompt, user_prompt)
            
        if not extracted_data:
            # Fallback to rule-based parser if no API key or API fails
            extracted_data = cls._run_heuristic_extraction(preprocessed_data)

        # 5. Clear old skills and insights from database
        skills_delete = select(Skill).where(Skill.repository_id == repository_id)
        skills_res = await db.execute(skills_delete)
        for s in skills_res.scalars().all():
            await db.delete(s)

        insight_delete = select(ProjectInsight).where(ProjectInsight.repository_id == repository_id)
        insight_res = await db.execute(insight_delete)
        for ins in insight_res.scalars().all():
            await db.delete(ins)

        # 6. Save newly extracted skills
        for skill_dict in extracted_data.get("skills", []):
            skill_name = skill_dict.get("name", "").strip()
            if not skill_name:
                continue
            db.add(Skill(
                repository_id=repository_id,
                skill_name=skill_name,
                confidence_score=max(0, min(100, int(skill_dict.get("confidence", 70)))),
                category=skill_dict.get("category", "Software Engineering"),
                evidence=skill_dict.get("evidence", [])
            ))

        # 7. Save project insight summaries
        insight = ProjectInsight(
            repository_id=repository_id,
            project_type=extracted_data.get("project_type", "Web Application"),
            project_category=extracted_data.get("project_category", ["Backend Development"]),
            project_summary=extracted_data.get("project_summary", "")[:4096],
            technical_summary=extracted_data.get("technical_summary", "")[:4096],
            complexity_level=extracted_data.get("complexity_level", "Intermediate")
        )
        db.add(insight)
        
        await db.commit()
        await db.refresh(insight)
        
        logger.info(f"Successfully saved skills and insights for repository_id={repository_id}. Insight ID={insight.id}")
        return insight

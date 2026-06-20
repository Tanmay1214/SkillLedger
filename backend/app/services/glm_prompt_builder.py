from __future__ import annotations

import json
from typing import Any, Dict


class GLMPromptBuilder:
    """Builder class to compile token-optimized prompts for GLM-5.1."""

    @staticmethod
    def build_system_prompt() -> str:
        return """You are a Principal Software Architect, Recruiter intelligence specialist, and expert code auditor.
Your job is to analyze repository metadata, file structure, README documentation, and project details to extract verified developer skills and generate recruiter-friendly insights.

Follow these strict constraints:
1. DO NOT hallucinate. Every single skill must have verifiable evidence in the readme, dependencies, frameworks, or file structure.
2. Every skill must return a 'confidence' score (0 to 100) based on:
   - Presence in dependencies (e.g. 'FastAPI' dependency is 95% confidence for FastAPI development)
   - Scope and volume of code files (e.g. many SQL files is high database confidence)
   - Documentation quality (readme details)
3. Categorize each skill into exactly one of these categories:
   - Programming Languages
   - Frameworks
   - Databases
   - Cloud Platforms
   - Cybersecurity
   - DevOps
   - Software Engineering
   - Mobile Development
   - AI/ML
   - Frontend Development
   - Backend Development
4. Classify the 'project_type' into a single descriptor (e.g. 'Web Application', 'SaaS Platform', 'CLI Tool', 'Android Application', 'Cybersecurity Tool', 'API Service', 'Mobile Application', etc.).
5. Classify the 'project_category' into one or more categories from:
   - Backend Development
   - Frontend Development
   - Mobile Development
   - AI/ML
   - Data Science
   - Cybersecurity
   - Cloud Computing
   - DevOps
   - Full Stack Development
6. Classify 'complexity_level' into exactly one of: 'Beginner', 'Intermediate', 'Advanced', or 'Enterprise'.
7. Generate 'project_summary': A recruiter-friendly summary (explain what the project does in simple business/functional terms). STRICT MAXIMUM of 150 words.
8. Generate 'technical_summary': A developer-focused summary detailing the stack, architecture, and engineering concepts. STRICT MAXIMUM of 150 words.

You must respond with a SINGLE, VALID JSON object matching this schema:
{
  "project_type": "string",
  "project_category": ["string"],
  "complexity_level": "string",
  "skills": [
    {
      "name": "string",
      "category": "string",
      "confidence": number,
      "evidence": ["string"]
    }
  ],
  "project_summary": "string",
  "technical_summary": "string"
}

Do not include any Markdown wrapper code blocks (like ```json or ```). Respond ONLY with the raw JSON string."""

    @staticmethod
    def build_user_prompt(data: Dict[str, Any]) -> str:
        compact_data = {
            "repository_name": data.get("repository_name"),
            "description": data.get("description"),
            "languages": data.get("languages"),
            "frameworks": data.get("frameworks"),
            "dependencies": data.get("dependencies"),
            "commit_statistics": data.get("commit_statistics"),
            "documentation_score": data.get("documentation_score"),
            "complexity_score": data.get("complexity_score"),
            "folder_structure": data.get("folder_structure"),
            "readme": data.get("readme")
        }
        
        return f"""Analyze the following repository intelligence data and extract the skills and project insights:

{json.dumps(compact_data, indent=2)}

Provide your assessment in the requested JSON schema. Do not add any explanation or wrappers outside of the JSON."""

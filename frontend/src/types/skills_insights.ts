/**
 * Types representing the GLM Skill Extraction Service outputs.
 */

export interface Skill {
  id: number;
  repository_id: number;
  skill_name: string;
  confidence_score: number;
  category: string;
  evidence: string[];
  created_at: string;
}

export interface ProjectInsight {
  id: number;
  repository_id: number;
  project_type: string;
  project_category: string[];
  project_summary: string;
  technical_summary: string;
  complexity_level: string;
  created_at: string;
}

export interface SkillExtractionResponse {
  status: string;
}

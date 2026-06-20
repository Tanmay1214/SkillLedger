from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Optional
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class GLMClient:
    """Async client to communicate with the GLM API (Zhipu AI)."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.glm_api_key
        # Fallback Zhipu AI Chat Completion API endpoint
        self.url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

    async def extract_project_metadata(self, system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
        """Sends prompts to the GLM API and returns the validated structured JSON response."""
        if not self.api_key:
            logger.info("No GLM_API_KEY configured. GLM API client will not execute request.")
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": "glm-4",  # Using the highly stable glm-4 model
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }

        max_retries = 3
        timeout = httpx.Timeout(20.0, read=15.0)

        for attempt in range(1, max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    logger.info(f"Sending request to GLM API, attempt {attempt}/{max_retries}")
                    resp = await client.post(self.url, json=payload, headers=headers)
                    
                    if resp.status_code == 200:
                        res_data = resp.json()
                        choices = res_data.get("choices", [])
                        if not choices:
                            logger.warning("GLM response had no choices.")
                            continue
                            
                        content = choices[0].get("message", {}).get("content", "")
                        if not content:
                            logger.warning("GLM choice content was empty.")
                            continue
                            
                        # Clean potential markdown block formatting
                        clean_content = re.sub(r"```(?:json)?\s*|```", "", content).strip()
                        try:
                            parsed_json = json.loads(clean_content)
                            # Basic validation of expected keys
                            required_keys = ["project_type", "project_category", "complexity_level", "skills", "project_summary", "technical_summary"]
                            if all(k in parsed_json for k in required_keys):
                                return parsed_json
                            else:
                                logger.warning(f"GLM JSON missing required keys: {parsed_json.keys()}")
                        except json.JSONDecodeError:
                            logger.error(f"Failed to parse GLM content as JSON: {clean_content}")
                    
                    elif resp.status_code == 429:
                        logger.warning(f"GLM API Rate Limited (429). Attempt {attempt}.")
                    else:
                        logger.error(f"GLM API error {resp.status_code}: {resp.text}")
                        
            except httpx.RequestError as e:
                logger.warning(f"HTTP connection failed during GLM call: {e}")

        logger.error("Failed to fetch repository intelligence from GLM API after multiple retries.")
        return None

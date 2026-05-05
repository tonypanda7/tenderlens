"""
TenderLens — F-02 Tender Analysis: Gemini Criterion Extractor

Reads tender PDF, sends to Gemini 2.5 Flash with versioned prompt,
validates JSON response against CriterionSchema (Pydantic).
"""

import json
from typing import List, Dict, Any, Optional

from google import genai
from google.genai import types

from app.config import settings
from app.shared.schemas import CriterionBase, ThresholdSchema


PROMPT_VERSION = "extract_v2"


class TenderCriterionExtractor:
    """
    Extracts eligibility criteria from a tender PDF using Gemini 2.5 Flash.
    The prompt is versioned — version is recorded in every criterion row.
    """

    def __init__(self):
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = "gemini-2.5-flash"
        self.prompt_version = PROMPT_VERSION

    async def extract_criteria(
        self,
        tender_text: str,
        tender_id: str,
    ) -> Dict[str, Any]:
        """
        Send full tender PDF text to Gemini 2.5 Flash.
        Returns structured criterion registry JSON.
        """
        prompt = self._build_extraction_prompt(tender_text)

        try:
            import asyncio as _asyncio

            last_error = None
            for attempt in range(settings.gemini_max_retries):
                try:
                    response = await self.client.aio.models.generate_content(
                        model=self.model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.1,
                            response_mime_type="application/json",
                        ),
                    )
                    last_error = None
                    break  # Success
                except Exception as retry_err:
                    last_error = retry_err
                    err_str = str(retry_err)
                    if "503" in err_str or "UNAVAILABLE" in err_str or "overloaded" in err_str.lower():
                        wait = 2 ** attempt  # 1s, 2s, 4s, 8s
                        await _asyncio.sleep(wait)
                        continue
                    raise  # Non-retryable error

            if last_error:
                raise last_error

            raw_criteria = json.loads(response.text)
            print(f"DEBUG extractor: raw Gemini response type={type(raw_criteria)}, preview={str(raw_criteria)[:500]}")

            # Validate each criterion against Pydantic schema
            validated_criteria = []
            if isinstance(raw_criteria, dict) and "criteria" in raw_criteria:
                criteria_list = raw_criteria["criteria"]
            elif isinstance(raw_criteria, list):
                criteria_list = raw_criteria
            else:
                criteria_list = []

            print(f"DEBUG extractor: found {len(criteria_list)} raw criteria from Gemini")

            for c in criteria_list:
                try:
                    # Parse threshold if present
                    threshold = None
                    if c.get("threshold"):
                        threshold = ThresholdSchema(**c["threshold"])

                    criterion = CriterionBase(
                        criterion_id=c.get("criterion_id", f"C{len(validated_criteria)+1}"),
                        text=c.get("text", ""),
                        type=c.get("type", "compliance"),
                        mandatory=c.get("mandatory", True),
                        threshold=threshold,
                        source_section=c.get("source_section"),
                        source_page=c.get("source_page"),
                        weight=c.get("weight", 0.0),
                        ambiguous=c.get("ambiguous", False),
                        ambiguity_note=c.get("ambiguity_note"),
                    )
                    validated_criteria.append(criterion)
                except Exception as val_err:
                    print(f"DEBUG extractor: validation error for criterion {c.get('criterion_id', '?')}: {val_err}")
                    continue  # Skip malformed criteria

            print(f"DEBUG extractor: validated {len(validated_criteria)} criteria")

            return {
                "tender_id": tender_id,
                "prompt_version": self.prompt_version,
                "criteria": [c.model_dump() for c in validated_criteria],
                "raw_response": raw_criteria,
            }

        except Exception as e:
            print(f"DEBUG extractor: EXCEPTION: {e}")
            return {
                "tender_id": tender_id,
                "prompt_version": self.prompt_version,
                "criteria": [],
                "error": str(e),
            }

    def _build_extraction_prompt(self, tender_text: str) -> str:
        """
        Build the versioned extraction prompt.
        Stored in services/api/features/tender_analysis/prompts/extract_v2.py
        """
        return f"""You are an expert in Indian government procurement. Your task is to extract ALL eligibility criteria from the following tender document.

INSTRUCTIONS:
1. Read the ENTIRE document carefully.
2. Extract every eligibility criterion — financial, technical, compliance, and conditional.
3. For each criterion, identify:
   - A unique ID (C1, C2, C3, ...)
   - The exact text of the criterion
   - Type: financial | technical | compliance | conditional
   - Whether it is mandatory or optional
   - The threshold (value, unit, operator)
   - The source section and page number
   - A suggested weight (as percentage, all weights should sum to 100)
   - Whether the criterion is ambiguous (appears in multiple sections with different values)
4. If a criterion appears in two sections with different thresholds, set "ambiguous": true and include an "ambiguity_note".
5. For conditional criteria (like MSME exemptions), specify the effect on other criteria.

CHAIN OF THOUGHT: First list each criterion you find with its section reference, then structure your final JSON.

Return ONLY a valid JSON object with this structure:
{{
  "criteria": [
    {{
      "criterion_id": "C1",
      "text": "description of the criterion",
      "type": "financial",
      "mandatory": true,
      "threshold": {{
        "value": 5,
        "unit": "crore_inr",
        "period": "FY22-FY24",
        "operator": "gte"
      }},
      "source_section": "Section 4.1",
      "source_page": 7,
      "weight": 35,
      "ambiguous": false,
      "ambiguity_note": null
    }}
  ]
}}

FEW-SHOT EXAMPLES:
1. Financial: "Average annual turnover for last 3 FY >= Rs. 5 Crore" → type: financial, threshold: {{value: 5, unit: crore_inr, operator: gte}}
2. Technical: "Minimum 3 similar works completed in last 5 years, each above Rs. 1.5 Cr" → type: technical, threshold: {{value: 3, unit: works, each_value: 1.5, each_unit: crore_inr, operator: gte}}
3. Conditional: "MSME registered firms exempted from turnover threshold" → type: conditional, threshold: {{effect: "exempts_C1_turnover_threshold", operator: "modifier"}}

TENDER DOCUMENT TEXT:
{tender_text}
"""

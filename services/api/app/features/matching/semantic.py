"""
TenderLens — Semantic Matcher (Gemini-powered)
Called ONLY for criteria with operator: "semantic_match".
All numeric/boolean criteria bypass this entirely and use pure math.

Flow:
  1. Receives: tender_requirement (text) + bidder_extracted_value (text)
  2. Sends both to Gemini 2.5 Flash with a focused comparison prompt
  3. Gemini returns: {match: true/false, confidence: 0.0-1.0, reasoning: "..."}
  4. Result is passed to the deterministic engine as a boolean
"""

import json
from typing import Dict, Any

from google import genai
from google.genai import types

from app.config import settings


SEMANTIC_COMPARISON_PROMPT = """You are a procurement domain expert. Compare the TENDER REQUIREMENT against the BIDDER'S SUBMITTED VALUE and determine if the bidder meets the requirement.

RULES:
1. Use domain knowledge. Materials, grades, and specifications often have multiple valid names.
   - "Lycra" = "Spandex" = "Elastane" (same material)
   - "Performance Polyester" = "High-tenacity PET fiber" (acceptable match)
   - "M40 Concrete" != "M30 Concrete" (different grade, NOT a match)
   - "Single Jersey" = "Plain Knit" = "Circular Knit" (same knit type)
   - "Fe 500D TMT" != "Fe 415 TMT" (different grade)

2. Consider the INTENT of the requirement, not just exact words.
   - If tender says "Four span yarn" and bidder says "4-ply yarn", that is a match.
   - If tender says "NABCB accredited ISO 9001" and bidder says "ISO 9001:2015 by QCI", check if QCI is NABCB-accredited.

3. Partial matches are NOT acceptable. The bidder must fully satisfy the requirement.
   - Tender: "92% Polyester, 8% Lycra" + Bidder: "100% Polyester" -> NOT a match (missing Lycra component).

4. If you are uncertain (< 70% sure), output match: false and explain why in reasoning.

Return ONLY valid JSON:
{{
  "match": true | false,
  "confidence": 0.0 to 1.0,
  "reasoning": "Brief explanation of why this matches or does not match"
}}

TENDER REQUIREMENT:
{tender_requirement}

BIDDER'S SUBMITTED VALUE:
{bidder_value}
"""


class SemanticMatcher:
    """
    Uses Gemini 2.5 Flash to semantically compare text-based criteria.
    Only called for operator: "semantic_match". All other operators
    are handled by pure math in the NormalisationEngine.
    """

    def __init__(self):
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = "gemini-2.5-flash"

    async def compare(
        self,
        tender_requirement: str,
        bidder_value: str,
    ) -> Dict[str, Any]:
        """
        Compare a tender requirement against a bidder's submitted value.

        Returns:
            {
                "match": bool,
                "confidence": float (0.0-1.0),
                "reasoning": str,
                "raw_response": dict
            }
        """
        prompt = SEMANTIC_COMPARISON_PROMPT.format(
            tender_requirement=tender_requirement,
            bidder_value=bidder_value,
        )

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.05,  # Near-deterministic for consistency
                    response_mime_type="application/json",
                ),
            )

            result = json.loads(response.text)

            return {
                "match": bool(result.get("match", False)),
                "confidence": float(result.get("confidence", 0.0)),
                "reasoning": str(result.get("reasoning", "")),
                "raw_response": result,
            }

        except Exception as e:
            # On failure, return no-match with zero confidence
            # This forces it into the reviewer queue for human decision
            return {
                "match": False,
                "confidence": 0.0,
                "reasoning": f"Semantic comparison failed: {str(e)}",
                "raw_response": {},
            }


semantic_matcher = SemanticMatcher()

"""
TenderLens — F-05 Rationale Generator
Uses Gemini 2.5 Flash to produce 'why-this-bidder' explanations.
Stage 3: One call on score summaries only (no raw docs).
"""

import json
from typing import List, Dict, Any

from google import genai
from google.genai import types

from app.config import settings


class RationaleGenerator:
    """
    Generates plain-English rationale for each bidder's ranking.
    Uses Gemini 2.5 Flash with score summaries only — no raw documents.
    """

    def __init__(self):
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = "gemini-2.5-flash"

    async def generate_rationales(
        self,
        ranked_bidders: List[Dict[str, Any]],
        tender_title: str,
    ) -> List[Dict[str, Any]]:
        """
        Generate rationale for all ranked bidders in a single Gemini call.
        ~3k tokens total — summaries only, no raw docs.
        """
        # Build compact summaries for each bidder
        summaries = []
        for b in ranked_bidders:
            scores_summary = ", ".join([
                f"{cs.get('criterion_id', '?')}: {cs.get('verdict', '?')} "
                f"({cs.get('normalised_score', 0):.2f})"
                for cs in b.get("criterion_scores", [])
            ])
            summaries.append(
                f"Rank #{b.get('rank', '?')} — {b.get('bidder_name', 'Unknown')} — "
                f"Score: {b.get('final_score', 0):.1f}/100 — "
                f"Criteria: [{scores_summary}]"
            )

        summaries_text = "\n".join(summaries)

        prompt = f"""You are generating a comparative ranking rationale for tender: "{tender_title}".

RANKED BIDDERS (score summaries only):
{summaries_text}

TASK: For each bidder, write a 2-3 sentence plain-English explanation of why they rank where they do.
Compare each bidder to others — mention specific strengths and weaknesses relative to the field.

Return a JSON array where each element has:
- "bidder_name": string
- "rank": number
- "rationale": string (2-3 sentences, plain English)

Return ONLY valid JSON. No markdown fences.
"""

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    response_mime_type="application/json",
                ),
            )

            rationales = json.loads(response.text)

            # Merge rationales back into ranked_bidders
            rationale_map = {
                r.get("bidder_name", ""): r.get("rationale", "")
                for r in rationales
            }

            for bidder in ranked_bidders:
                name = bidder.get("bidder_name", "")
                bidder["rationale"] = rationale_map.get(name, "Rationale not generated.")

            return ranked_bidders

        except Exception as e:
            # Fallback: generate simple rationale from scores
            for bidder in ranked_bidders:
                bidder["rationale"] = (
                    f"Ranked #{bidder.get('rank', '?')} with a score of "
                    f"{bidder.get('final_score', 0):.1f}/100. "
                    f"Rationale generation failed: {str(e)}"
                )
            return ranked_bidders

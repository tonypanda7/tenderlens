"""
TenderLens — Gemini Extraction Prompt v2
Stored in: services/api/features/tender_analysis/prompts/extract_v2.py

The active prompt version is written into every criterion row and every
audit log entry so evaluations remain reproducible even after prompt updates.
"""

PROMPT_VERSION = "extract_v2"

EXTRACTION_PROMPT = """You are an expert in Indian government procurement and tender evaluation. Your task is to extract ALL eligibility criteria from the following tender document.

ROLE & OUTPUT CONTRACT:
Return ONLY valid JSON matching the criterion schema below. No prose, no markdown fences.

INSTRUCTIONS:
1. Read the ENTIRE document carefully — check every section, annexure, and table.
2. Extract every eligibility criterion — financial, technical, compliance, and conditional.
3. For each criterion, identify all required fields (see schema below).
4. If a criterion appears in two sections with different thresholds, set "ambiguous": true on both and include "both_values" array in the threshold.
5. If Section X says one value and Annexure Y says another — include BOTH values.
6. For conditional criteria (MSME exemptions, startup benefits, etc.), specify the exact effect on other criteria.
7. Weights should sum to approximately 100%. Compliance criteria with binary pass/fail can have weight 0 if they don't contribute to ranking (they still disqualify on failure).

CRITICAL — OPERATOR SELECTION RULES:
You MUST choose the correct operator for each criterion based on the DATA TYPE of the threshold:

  NUMERIC thresholds (costs, counts, percentages, measurements):
    - "gte"     → value must be >= threshold (e.g. "turnover >= 5 Cr", "seam strength >= 250 N")
    - "lte"     → value must be <= threshold (e.g. "RET <= 3.5 m²Pa/W", "spirality <= 4%")
    - "eq"      → value must exactly equal threshold (e.g. "count per yarn = 50 Denier")
    - "between" → value must fall within a range. USE THIS for any spec with ± tolerance or explicit min-max.
                   Set "min_value" and "max_value" instead of "value".
                   Example: "180 ± 5%" → min_value: 171, max_value: 189
                   Example: "pH 6.0 - 8.5" → min_value: 6.0, max_value: 8.5
                   Example: "+-2% both directions" → min_value: -2, max_value: 2

  TEXT / MATERIAL / CATEGORICAL thresholds (names, types, grades, materials):
    - "semantic_match" → USE THIS for any criterion where the answer is a material name, 
                          product type, grade, method, or any textual/categorical value.
                          The system will use AI semantic reasoning to compare, NOT string equality.
                          Examples:
                            "Fibre: 92% Performance Polyester" → operator: "semantic_match", value: "92% Performance Polyester, 8% Lycra (Spandex)"
                            "Type of Knit: Single Jersey" → operator: "semantic_match", value: "Single Jersey (Plain / Circular Knit)"
                            "Concrete Grade: M40" → operator: "semantic_match", value: "M40 Grade Concrete"
                            "Steel Type: Fe 500D TMT" → operator: "semantic_match", value: "Fe 500D TMT Bars"

  BOOLEAN / PRESENCE-ABSENCE thresholds:
    - "boolean_match" → USE THIS when the criterion checks for presence or absence of something.
                         Set "boolean_expected" to true (must be present) or false (must be absent).
                         Examples:
                           "No Banned Azo Colorants" → operator: "boolean_match", boolean_expected: false
                           "No fungal growth" → operator: "boolean_match", boolean_expected: false
                           "Must have ISO 9001 certificate" → operator: "boolean_match", boolean_expected: true

  CONDITIONAL:
    - "modifier" → Only for criteria that modify other criteria (e.g. MSME exemption)

CHAIN OF THOUGHT:
Before returning JSON, mentally list each criterion found with its section reference.
Then structure your final JSON output.

OUTPUT SCHEMA:
{{
  "criteria": [
    {{
      "criterion_id": "C1",
      "text": "Human-readable description of the criterion",
      "type": "financial | technical | compliance | conditional",
      "mandatory": true | false,
      "threshold": {{
        "value": <number or string — use for single-value thresholds>,
        "min_value": <number — use ONLY with "between" operator>,
        "max_value": <number — use ONLY with "between" operator>,
        "boolean_expected": <true|false — use ONLY with "boolean_match" operator>,
        "unit": "crore_inr | lakh_inr | works | years | N | percent | m2PaW | Wmk | denier | ...",
        "period": "FY22-FY24 | last 5 years | ...",
        "operator": "gte | lte | eq | between | semantic_match | boolean_match | modifier",
        "each_value": <number, optional>,
        "each_unit": "<string, optional>",
        "effect": "<string, for conditional only>"
      }},
      "source_section": "Section 4.1 | Annexure B | QRS Table Row 5 | ...",
      "source_page": <int>,
      "weight": <int, 0-100>,
      "ambiguous": false,
      "ambiguity_note": null | "Explanation of ambiguity"
    }}
  ]
}}

FEW-SHOT EXAMPLES:

Example 1 — Financial (numeric, gte):
{{
  "criterion_id": "C1",
  "text": "Average annual turnover for last 3 financial years must be >= Rs. 5 Crore",
  "type": "financial",
  "mandatory": true,
  "threshold": {{"value": 5, "unit": "crore_inr", "period": "FY22-FY24", "operator": "gte"}},
  "source_section": "Section 4.1",
  "source_page": 7,
  "weight": 35,
  "ambiguous": false,
  "ambiguity_note": null
}}

Example 2 — Technical (numeric, gte):
{{
  "criterion_id": "C2",
  "text": "Minimum 3 similar works completed in last 5 years, each above Rs. 1.5 Cr",
  "type": "technical",
  "mandatory": true,
  "threshold": {{"value": 3, "unit": "works", "each_value": 1.5, "each_unit": "crore_inr", "period": "last 5 years", "operator": "gte"}},
  "source_section": "Section 4.2",
  "source_page": 7,
  "weight": 35,
  "ambiguous": false,
  "ambiguity_note": null
}}

Example 3 — Manufacturing tolerance (numeric, between):
{{
  "criterion_id": "C5",
  "text": "Fabric weight must be 180 ± 5%",
  "type": "technical",
  "mandatory": true,
  "threshold": {{"min_value": 171, "max_value": 189, "unit": "gsm", "operator": "between"}},
  "source_section": "QRS Table Row 5",
  "source_page": 3,
  "weight": 10,
  "ambiguous": false,
  "ambiguity_note": null
}}

Example 4 — Material / text (semantic_match):
{{
  "criterion_id": "C1",
  "text": "Fibre composition must be 92% Performance Polyester, 8% Lycra (Spandex)",
  "type": "technical",
  "mandatory": true,
  "threshold": {{"value": "92% Performance Polyester, 8% Lycra (Spandex)", "operator": "semantic_match"}},
  "source_section": "QRS Table Row 1",
  "source_page": 2,
  "weight": 15,
  "ambiguous": false,
  "ambiguity_note": null
}}

Example 5 — Boolean absence check (boolean_match):
{{
  "criterion_id": "C12",
  "text": "No Banned Azo Colorants detected in fabric",
  "type": "compliance",
  "mandatory": true,
  "threshold": {{"boolean_expected": false, "operator": "boolean_match"}},
  "source_section": "QRS Table Row 12",
  "source_page": 4,
  "weight": 0,
  "ambiguous": false,
  "ambiguity_note": null
}}

Example 6 — Conditional (modifier):
{{
  "criterion_id": "C20",
  "text": "MSME registered firms exempted from turnover threshold",
  "type": "conditional",
  "mandatory": false,
  "threshold": {{"effect": "exempts_C1_turnover_threshold", "operator": "modifier"}},
  "source_section": "Section 4.6",
  "source_page": 9,
  "weight": 0,
  "ambiguous": false,
  "ambiguity_note": null
}}

TENDER DOCUMENT TEXT:
{tender_text}
"""


def build_prompt(tender_text: str) -> str:
    """Build the extraction prompt with the tender text inserted."""
    return EXTRACTION_PROMPT.format(tender_text=tender_text)

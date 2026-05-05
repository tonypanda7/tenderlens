"""
TenderLens — F-05 Scoring Engine
Deterministic weighted score computation + ranking.
"""

from typing import List, Dict, Any, Optional

from app.features.matching.engine import WeightedScoreCalculator, NormalisationEngine


class ScoringEngine:
    """
    Orchestrates the full scoring pipeline for all bidders in a tender.

    1. Collects all verdicts per bidder
    2. Normalises scores by criterion type
    3. Applies weighted formula
    4. Ranks eligible bidders
    5. Separates disqualified bidders
    """

    def __init__(self):
        self.calculator = WeightedScoreCalculator()
        self.normaliser = NormalisationEngine()

    def score_bidder(
        self,
        bidder_id: str,
        bidder_name: str,
        verdicts: List[Dict[str, Any]],
        criteria: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Score a single bidder against all criteria verdicts.
        Returns complete score breakdown.
        """
        criterion_scores = []

        for criterion in criteria:
            cid = criterion["criterion_id"]

            # Find the verdict for this criterion
            verdict = next(
                (v for v in verdicts if v.get("criterion_id") == cid),
                None,
            )

            if verdict is None:
                # No verdict found — criterion was not evaluated
                criterion_scores.append({
                    "criterion_id": cid,
                    "normalised_score": 0.0,
                    "weight": criterion.get("weight", 0.0),
                    "mandatory": criterion.get("mandatory", False),
                    "verdict": "not_found",
                    "disqualify_detail": f"No evaluation found for criterion {cid}",
                })
                continue

            # Get threshold and operator
            threshold = criterion.get("threshold_json", {}) or {}
            operator = threshold.get("operator", "boolean_match")
            ctype = criterion.get("type", "compliance")

            # If verdict already has normalised_score from matching pipeline, use it
            normalised = verdict.get("normalised_score", 0.0)
            formula = f"From matching pipeline: {verdict.get('verdict', 'unknown')}"

            # If normalised_score is 0 but verdict is pass, recalculate
            if normalised == 0.0 and verdict.get("verdict") == "pass":
                normalised = 1.0
                formula = "Verdict: pass → 1.0"

            # For financial/technical criteria with numeric extracted values, try ratio scoring
            extracted_value = verdict.get("extracted_value")
            if ctype == "financial" and extracted_value is not None:
                bidder_value = self._extract_numeric(str(extracted_value))
                threshold_value = threshold.get("value", 0)
                if isinstance(threshold_value, (int, float)) and threshold_value > 0 and bidder_value is not None:
                    normalised, formula = self.normaliser.evaluate(
                        operator=operator,
                        bidder_value=bidder_value,
                        threshold=threshold,
                        criterion_type=ctype,
                    )

            elif ctype == "technical" and extracted_value is not None:
                bidder_count = self._extract_count(str(extracted_value))
                threshold_value = threshold.get("value", 0)
                if isinstance(threshold_value, (int, float)) and threshold_value > 0 and bidder_count is not None:
                    normalised, formula = self.normaliser.evaluate(
                        operator=operator,
                        bidder_value=bidder_count,
                        threshold=threshold,
                        criterion_type=ctype,
                    )

            weighted = (criterion.get("weight", 0.0) / 100.0) * normalised * 100.0

            criterion_scores.append({
                "criterion_id": cid,
                "extracted_value": verdict.get("extracted_value"),
                "source_block": verdict.get("source_block"),
                "source_page": verdict.get("source_page"),
                "normalised_score": normalised,
                "weighted_score": round(weighted, 2),
                "weight": criterion.get("weight", 0.0),
                "mandatory": criterion.get("mandatory", False),
                "verdict": verdict.get("verdict", "not_found"),
                "confidence": verdict.get("confidence", 0.0),
                "layer": verdict.get("layer", "unknown"),
                "auto_approved": verdict.get("auto_approved", False),
                "formula": formula,
                "disqualify_detail": (
                    f"{criterion.get('text', cid)} — {verdict.get('verdict', 'not_found')}"
                    if criterion.get("mandatory") and normalised == 0.0
                    else None
                ),
            })

        # Calculate final weighted score
        result = self.calculator.calculate(criterion_scores)

        return {
            "bidder_id": bidder_id,
            "bidder_name": bidder_name,
            "final_score": result["final_score"],
            "eligible": result["eligible"],
            "disqualified": result["disqualified"],
            "disqualify_reason": result["disqualify_reason"],
            "criterion_scores": criterion_scores,
            "formula": result["formula"],
        }

    def rank_bidders(
        self,
        scored_bidders: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Rank all eligible bidders by final_score descending.
        Disqualified bidders are separated.
        """
        eligible = [b for b in scored_bidders if not b.get("disqualified", False)]
        disqualified = [b for b in scored_bidders if b.get("disqualified", False)]

        # Sort eligible by score descending
        eligible.sort(key=lambda x: x.get("final_score", 0), reverse=True)

        # Assign ranks
        for rank, bidder in enumerate(eligible, start=1):
            bidder["rank"] = rank

        return {
            "total_bidders": len(scored_bidders),
            "eligible_count": len(eligible),
            "disqualified_count": len(disqualified),
            "rankings": eligible,
            "disqualified": disqualified,
        }

    @staticmethod
    def _extract_numeric(value: Optional[str]) -> Optional[float]:
        """Extract numeric value from a string."""
        from app.features.matching.engine import DeterministicMatcher
        if value is None:
            return None
        return DeterministicMatcher.extract_numeric_value(str(value))

    @staticmethod
    def _extract_count(value: Optional[str]) -> Optional[int]:
        """Extract count from text like '4 works' or '5'."""
        import re
        if value is None:
            return None
        match = re.search(r"(\d+)", str(value))
        return int(match.group(1)) if match else None

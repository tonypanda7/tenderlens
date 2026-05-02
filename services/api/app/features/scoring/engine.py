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

            # Normalise based on criterion type
            ctype = criterion.get("type", "compliance")
            threshold = criterion.get("threshold_json", {}) or {}

            if ctype == "financial":
                bidder_value = self._extract_numeric(verdict.get("extracted_value"))
                threshold_value = threshold.get("value", 0)
                if isinstance(threshold_value, (int, float)) and threshold_value > 0 and bidder_value is not None:
                    normalised, formula = self.normaliser.normalise_financial(
                        bidder_value, threshold_value
                    )
                else:
                    normalised = 1.0 if verdict.get("verdict") == "pass" else 0.0
                    formula = f"Semantic verdict: {verdict.get('verdict')}"

            elif ctype == "technical":
                bidder_count = self._extract_count(verdict.get("extracted_value"))
                required_count = threshold.get("value", 0)
                if isinstance(required_count, (int, float)) and required_count > 0 and bidder_count is not None:
                    normalised, formula = self.normaliser.normalise_technical(
                        int(bidder_count), int(required_count)
                    )
                else:
                    normalised = 1.0 if verdict.get("verdict") == "pass" else 0.0
                    formula = f"Semantic verdict: {verdict.get('verdict')}"

            elif ctype == "compliance":
                passes = verdict.get("verdict") == "pass"
                normalised, formula = self.normaliser.normalise_compliance(passes)

            elif ctype == "conditional":
                has_condition = verdict.get("verdict") == "pass"
                normalised, formula, _ = self.normaliser.normalise_conditional(has_condition)

            else:
                normalised = 1.0 if verdict.get("verdict") == "pass" else 0.0
                formula = f"Unknown type '{ctype}' — binary scoring"

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

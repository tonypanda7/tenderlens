"""
TenderLens — F-04 Matching Engine
Three-stage matching pipeline: deterministic → semantic → computation.
This is the CORE deterministic logic of the system.
"""

import re
import hashlib
from datetime import datetime, date
from typing import Optional, Dict, Any, List, Tuple

from app.config import settings


# ══════════════════════════════════════════════════════════
# STAGE 1: DETERMINISTIC PRE-FILTER
# Zero API calls — pure Python rules engine
# ══════════════════════════════════════════════════════════

class DeterministicMatcher:
    """
    Runs deterministic checks that require zero external API calls.
    GSTIN regex, registration numbers, date validity, mandatory doc presence.
    """

    # ── Indian GSTIN regex ──
    # Format: 2 digits (state) + 10 char PAN + 1 digit (entity) + Z + 1 check char
    GSTIN_PATTERN = re.compile(
        r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
    )

    # ── PAN number regex ──
    PAN_PATTERN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$")

    # ── Common registration number patterns ──
    REG_NUMBER_PATTERN = re.compile(r"^[A-Z0-9]{5,20}$")

    @staticmethod
    def validate_gstin(value: str) -> Tuple[bool, float, str]:
        """
        Validate GSTIN format.
        Returns: (is_valid, confidence, detail)
        """
        if not value:
            return False, 0.0, "GSTIN not found in document"

        cleaned = value.strip().upper().replace(" ", "").replace("-", "")

        if DeterministicMatcher.GSTIN_PATTERN.match(cleaned):
            # Verify checksum (simplified — full Luhn check can be added)
            return True, 0.98, f"Valid GSTIN format: {cleaned}"
        else:
            return False, 0.95, f"Invalid GSTIN format: {cleaned}"

    @staticmethod
    def validate_pan(value: str) -> Tuple[bool, float, str]:
        """Validate PAN number format."""
        if not value:
            return False, 0.0, "PAN not found in document"

        cleaned = value.strip().upper().replace(" ", "")

        if DeterministicMatcher.PAN_PATTERN.match(cleaned):
            return True, 0.98, f"Valid PAN: {cleaned}"
        return False, 0.95, f"Invalid PAN format: {cleaned}"

    @staticmethod
    def validate_date_validity(
        date_str: str,
        must_be_valid_on: Optional[str] = None
    ) -> Tuple[bool, float, str]:
        """
        Check if a certificate/registration date is still valid.
        Tries multiple date formats common in Indian government docs.
        """
        formats = [
            "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d",
            "%d.%m.%Y", "%d %b %Y", "%d %B %Y",
        ]

        parsed_date = None
        for fmt in formats:
            try:
                parsed_date = datetime.strptime(date_str.strip(), fmt).date()
                break
            except ValueError:
                continue

        if parsed_date is None:
            return False, 0.40, f"Could not parse date: {date_str}"

        check_date = date.today()
        if must_be_valid_on:
            for fmt in formats:
                try:
                    check_date = datetime.strptime(must_be_valid_on.strip(), fmt).date()
                    break
                except ValueError:
                    continue

        if parsed_date >= check_date:
            return True, 0.95, f"Date {parsed_date} is valid (on or after {check_date})"
        else:
            return False, 0.95, f"Date {parsed_date} has expired (before {check_date})"

    @staticmethod
    def check_mandatory_doc_presence(
        required_doc_types: List[str],
        submitted_doc_types: List[str],
    ) -> Tuple[bool, float, List[str]]:
        """
        Check if all mandatory document types were submitted.
        Returns: (all_present, confidence, missing_list)
        """
        missing = [
            doc for doc in required_doc_types
            if doc.lower() not in [s.lower() for s in submitted_doc_types]
        ]

        if not missing:
            return True, 0.99, []
        return False, 0.99, missing

    @staticmethod
    def extract_numeric_value(text: str) -> Optional[float]:
        """
        Extract numeric value from text like 'Rs. 7.24 Cr' or '5,00,000'.
        Handles Indian numbering (lakhs, crores).
        """
        if not text:
            return None

        text = text.strip().upper()

        # Remove currency symbols
        text = re.sub(r"(RS\.?|INR|₹)", "", text, flags=re.IGNORECASE).strip()

        # Handle Cr / Crore / L / Lakh multipliers
        multiplier = 1.0
        if re.search(r"\bCR(ORE)?S?\b", text, re.IGNORECASE):
            multiplier = 1e7  # 1 Crore = 10 million
            text = re.sub(r"\bCR(ORE)?S?\b", "", text, re.IGNORECASE).strip()
        elif re.search(r"\bL(AKH)?S?\b", text, re.IGNORECASE):
            multiplier = 1e5  # 1 Lakh = 100,000
            text = re.sub(r"\bL(AKH)?S?\b", "", text, re.IGNORECASE).strip()

        # Remove Indian-style commas (1,23,456 → 123456)
        text = text.replace(",", "")

        # Find the first numeric value
        match = re.search(r"[\d]+\.?\d*", text)
        if match:
            return float(match.group()) * multiplier

        return None


# ══════════════════════════════════════════════════════════
# STAGE 3: COMPUTATION LAYER
# Averages, sums, counts — formula and result both logged
# ══════════════════════════════════════════════════════════

class ComputationMatcher:
    """
    Handles numeric computations: averages, sums, counts.
    Formula and result are both logged for audit trail.
    """

    @staticmethod
    def compute_average(values: List[float]) -> Tuple[float, str]:
        """
        Compute average and return both result and formula string.
        """
        if not values:
            return 0.0, "No values to average"

        avg = sum(values) / len(values)
        formula = f"({' + '.join(f'{v:.2f}' for v in values)}) / {len(values)} = {avg:.2f}"
        return avg, formula

    @staticmethod
    def compute_sum(values: List[float]) -> Tuple[float, str]:
        """Compute sum with logged formula."""
        total = sum(values)
        formula = f"{' + '.join(f'{v:.2f}' for v in values)} = {total:.2f}"
        return total, formula

    @staticmethod
    def count_qualifying(
        items: List[Dict[str, Any]],
        min_value: Optional[float] = None,
        value_key: str = "value",
    ) -> Tuple[int, str]:
        """
        Count items meeting a minimum value threshold.
        """
        if min_value is None:
            count = len(items)
            formula = f"Total items: {count}"
            return count, formula

        qualifying = [
            item for item in items
            if item.get(value_key, 0) >= min_value
        ]
        count = len(qualifying)
        formula = (
            f"{count} items >= {min_value:.2f} out of {len(items)} total"
        )
        return count, formula


# ══════════════════════════════════════════════════════════
# NORMALISATION ENGINE
# Converts raw values to 0.0–1.0 scores by criterion type
# ══════════════════════════════════════════════════════════

class NormalisationEngine:
    """
    Generic Rules Engine — converts extracted values to normalised scores (0.0 to 1.0)
    using mathematical and logical operators. Replaces rigid Financial/Technical
    formulas with a schema-driven approach suitable for manufacturing tolerances.
    """

    @staticmethod
    def evaluate(
        operator: str,
        bidder_value: Any,
        threshold: Dict[str, Any],
        criterion_type: str = "compliance"
    ) -> Tuple[float, str]:
        """
        Evaluate any rule based on the operator.
        Returns (score, formula)
        """
        # If the criterion is non-technical/non-financial (like "compliance"),
        # everything is pass/fail (1.0 or 0.0). For scaled scoring, we calculate a ratio.
        is_scaled = criterion_type in ["financial", "technical"] and isinstance(bidder_value, (int, float))

        try:
            if operator == "gte":
                tv = threshold.get("value", 0)
                passes = float(bidder_value) >= float(tv)
                if is_scaled and tv > 0:
                    raw = float(bidder_value) / float(tv)
                    score = min(raw, 1.0)
                    return score, f"{bidder_value} >= {tv} → ratio {raw:.4f} capped at {score:.2f}"
                return (1.0, f"PASS: {bidder_value} >= {tv}") if passes else (0.0, f"FAIL: {bidder_value} < {tv}")

            elif operator == "lte":
                tv = threshold.get("value", 0)
                passes = float(bidder_value) <= float(tv)
                return (1.0, f"PASS: {bidder_value} <= {tv}") if passes else (0.0, f"FAIL: {bidder_value} > {tv}")

            elif operator == "eq":
                tv = threshold.get("value", 0)
                passes = float(bidder_value) == float(tv)
                return (1.0, f"PASS: {bidder_value} == {tv}") if passes else (0.0, f"FAIL: {bidder_value} != {tv}")

            elif operator == "between":
                min_v = threshold.get("min_value", 0)
                max_v = threshold.get("max_value", 0)
                passes = float(min_v) <= float(bidder_value) <= float(max_v)
                return (1.0, f"PASS: {min_v} <= {bidder_value} <= {max_v}") if passes else (0.0, f"FAIL: {bidder_value} outside [{min_v}, {max_v}]")

            elif operator == "eq_string":
                tv = str(threshold.get("value", "")).strip().lower()
                bv = str(bidder_value).strip().lower()
                passes = (tv == bv)
                return (1.0, f"PASS: '{bv}' matches '{tv}'") if passes else (0.0, f"FAIL: '{bv}' != '{tv}'")

            elif operator == "semantic_match":
                # bidder_value is either:
                #   a) A dict from SemanticMatcher: {"match": bool, "confidence": float, "reasoning": str}
                #   b) A simple boolean/string from a pre-resolved comparison
                if isinstance(bidder_value, dict):
                    match = bool(bidder_value.get("match", False))
                    conf = bidder_value.get("confidence", 0.0)
                    reason = bidder_value.get("reasoning", "")
                    required = str(threshold.get("value", ""))
                    if match:
                        return (1.0, f"PASS (conf={conf:.2f}): Semantic match for '{required}' — {reason}")
                    else:
                        return (0.0, f"FAIL (conf={conf:.2f}): Semantic mismatch for '{required}' — {reason}")
                else:
                    # Fallback: treat as simple boolean
                    actual = str(bidder_value).strip().lower() in ['true', 'yes', '1', 'pass']
                    return (1.0, f"PASS: Semantic match verified") if actual else (0.0, f"FAIL: Semantic mismatch")

            elif operator == "boolean_match":
                expected = bool(threshold.get("boolean_expected", True))
                # Treat missing/None as False if expected is True, etc.
                actual = str(bidder_value).strip().lower() in ['true', 'yes', '1', 'present', 'found'] if bidder_value else False
                if str(bidder_value).strip().lower() in ['false', 'no', '0', 'absent', 'not found', 'none']:
                    actual = False
                
                passes = (actual == expected)
                return (1.0, f"PASS: Match {expected}") if passes else (0.0, f"FAIL: Expected {expected}, got {actual}")

            elif operator == "modifier":
                return 0.0, "CONDITIONAL: Modifies other criteria, no direct score"
            
            else:
                return 0.0, f"ERROR: Unknown operator '{operator}'"

        except (ValueError, TypeError) as e:
            return 0.0, f"ERROR: Data type mismatch during evaluation — {str(e)}"


# ══════════════════════════════════════════════════════════
# WEIGHTED SCORE CALCULATOR
# Final deterministic scoring from PRD Section 5.3
# ══════════════════════════════════════════════════════════

class WeightedScoreCalculator:
    """
    Computes the final deterministic weighted score per bidder.

    Final score = Σ (criterion_weight × normalised_criterion_score)

    Disqualification rule:
        If any mandatory criterion score == 0.0 → bidder disqualified
    """

    @staticmethod
    def calculate(
        criterion_scores: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Calculate final weighted score from per-criterion verdicts.

        Each item in criterion_scores should have:
            - criterion_id: str
            - normalised_score: float (0.0 to 1.0)
            - weight: float (percentage, e.g. 35.0)
            - mandatory: bool
            - verdict: str (pass | fail | partial)

        Returns:
            {
                "final_score": float,
                "eligible": bool,
                "disqualified": bool,
                "disqualify_reason": str | None,
                "weighted_breakdown": list,
                "formula": str,
            }
        """
        total_score = 0.0
        breakdown = []
        disqualify_reasons = []

        for cs in criterion_scores:
            normalised = cs.get("normalised_score", 0.0)
            weight = cs.get("weight", 0.0)
            mandatory = cs.get("mandatory", False)
            criterion_id = cs.get("criterion_id", "unknown")

            weighted = (weight / 100.0) * normalised * 100.0  # Convert back to points
            total_score += weighted

            breakdown.append({
                "criterion_id": criterion_id,
                "normalised_score": normalised,
                "weight_pct": weight,
                "weighted_score": round(weighted, 2),
            })

            # Disqualification check: mandatory criterion with score 0
            if mandatory and normalised == 0.0:
                reason = cs.get("disqualify_detail", f"Mandatory criterion {criterion_id} failed")
                disqualify_reasons.append(reason)

        disqualified = len(disqualify_reasons) > 0
        disqualify_reason = "; ".join(disqualify_reasons) if disqualified else None

        # Build formula string for audit
        formula_parts = [
            f"({cs.get('criterion_id')}: {cs.get('weight', 0):.0f}% × {cs.get('normalised_score', 0):.2f})"
            for cs in criterion_scores
        ]
        formula = " + ".join(formula_parts) + f" = {total_score:.2f}"

        return {
            "final_score": round(total_score, 2),
            "eligible": not disqualified,
            "disqualified": disqualified,
            "disqualify_reason": disqualify_reason,
            "weighted_breakdown": breakdown,
            "formula": formula,
        }


# ══════════════════════════════════════════════════════════
# CONFIDENCE ROUTER
# Routes verdicts to auto-approve, reviewer queue, or flag
# ══════════════════════════════════════════════════════════

class ConfidenceRouter:
    """
    Routes extraction results based on confidence bands:
        >= 0.85  → auto-verdict (no human review)
        0.60–0.84 → reviewer queue
        < 0.60   → flagged with raw image
    """

    def __init__(
        self,
        auto_threshold: float = settings.auto_approve_confidence,
        review_threshold: float = settings.reviewer_queue_confidence,
    ):
        self.auto_threshold = auto_threshold
        self.review_threshold = review_threshold

    def route(self, confidence: float) -> Dict[str, Any]:
        """
        Determine routing for a given confidence score.
        """
        if confidence >= self.auto_threshold:
            return {
                "action": "auto_approve",
                "auto_approved": True,
                "needs_review": False,
                "flag_with_image": False,
                "detail": f"Confidence {confidence:.2f} >= {self.auto_threshold} — auto-approved",
            }
        elif confidence >= self.review_threshold:
            return {
                "action": "reviewer_queue",
                "auto_approved": False,
                "needs_review": True,
                "flag_with_image": False,
                "detail": f"Confidence {confidence:.2f} in range [{self.review_threshold}, {self.auto_threshold}) — sent to reviewer",
            }
        else:
            return {
                "action": "flag_with_image",
                "auto_approved": False,
                "needs_review": True,
                "flag_with_image": True,
                "detail": f"Confidence {confidence:.2f} < {self.review_threshold} — flagged with raw image",
            }


# ══════════════════════════════════════════════════════════
# AUDIT HASH CHAIN
# ══════════════════════════════════════════════════════════

class AuditHashChain:
    """
    Generates SHA-256 hash chain for audit log entries.
    this_hash = SHA-256(prev_hash + entry_id + payload)
    Tampering invalidates all subsequent hashes.
    """

    @staticmethod
    def compute_hash(prev_hash: Optional[str], entry_id: str, payload: str) -> str:
        """
        Compute hash for a new audit entry.
        """
        data = f"{prev_hash or ''}{entry_id}{payload}"
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    @staticmethod
    def compute_lock_hash(criterion_ids: List[str], thresholds: List[str]) -> str:
        """
        Compute lock_hash = SHA-256 of sorted criterion IDs + thresholds.
        Used to make the criterion registry immutable once locked.
        """
        combined = sorted(criterion_ids)
        combined.extend(sorted(thresholds))
        data = "|".join(combined)
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    @staticmethod
    def verify_chain(entries: List[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
        """
        Verify an entire hash chain. Returns (is_valid, first_invalid_id).
        """
        for i, entry in enumerate(entries):
            prev_hash = entries[i - 1]["this_hash"] if i > 0 else None
            expected = AuditHashChain.compute_hash(
                prev_hash, entry["id"], str(entry["payload"])
            )
            if expected != entry["this_hash"]:
                return False, entry["id"]
        return True, None

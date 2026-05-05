"""
TenderLens — F-04 Matching Celery Tasks
Implements the three-stage matching pipeline: deterministic → semantic → computation.
"""

from typing import List, Dict, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.celery_app import celery_app
from app.shared.models import Bidder, IngestFile, OcrBlock, Criterion, Verdict, Extraction
from app.features.matching.engine import (
    DeterministicMatcher, NormalisationEngine, ConfidenceRouter, ComputationMatcher
)


async def run_matching_for_bidder(
    db: AsyncSession,
    tender_id: str,
    bidder_id: str,
    criteria: List[Dict[str, Any]],
):
    """
    Run the three-stage matching pipeline for a single bidder.
    Called directly by the evaluate endpoint (async context).

    Stage 1: Deterministic pre-filter (GSTIN, dates, doc presence)
    Stage 2: Gemini semantic matching (label resolution)
    Stage 3: Computation (averages, sums, counts)
    """
    # Load bidder's OCR blocks from DB
    result = await db.execute(
        select(IngestFile).where(IngestFile.bidder_id == bidder_id)
    )
    files = result.scalars().all()
    file_ids = [f.id for f in files]

    all_text = ""
    blocks_by_page = {}

    if file_ids:
        blocks_result = await db.execute(
            select(OcrBlock).where(OcrBlock.file_id.in_(file_ids)).order_by(OcrBlock.page_number)
        )
        blocks = blocks_result.scalars().all()

        for block in blocks:
            all_text += block.text + "\n"
            page = block.page_number
            if page not in blocks_by_page:
                blocks_by_page[page] = []
            blocks_by_page[page].append({
                "block_id": block.block_id,
                "text": block.text,
                "confidence": block.confidence,
                "type": block.type,
                "page_number": page,
            })

    # If no OCR blocks found, use file names as minimal evidence
    submitted_doc_types = [f.original_filename or "" for f in files]
    submitted_mime_types = [f.mime_type for f in files]

    # Delete existing verdicts for this bidder (supports re-evaluation)
    existing_verdicts = await db.execute(
        select(Verdict).where(Verdict.bidder_id == bidder_id)
    )
    for v in existing_verdicts.scalars().all():
        await db.delete(v)
    await db.flush()

    confidence_router = ConfidenceRouter()
    normaliser = NormalisationEngine()

    # Get criterion DB records for FK references
    criterion_result = await db.execute(
        select(Criterion).where(Criterion.tender_id == tender_id)
    )
    criterion_records = {c.criterion_id: c for c in criterion_result.scalars().all()}

    for criterion in criteria:
        cid = criterion["criterion_id"]
        ctype = criterion.get("type", "compliance")
        threshold = criterion.get("threshold_json") or {}
        operator = threshold.get("operator", "boolean_match")
        mandatory = criterion.get("mandatory", False)
        criterion_text = criterion.get("text", "")

        # Get the DB record for FK
        criterion_record = criterion_records.get(cid)
        if not criterion_record:
            continue

        extracted_value = None
        confidence = 0.0
        layer = "deterministic"
        source_page = None

        # ── STAGE 1: Deterministic Pre-Filter ──
        if operator == "boolean_match":
            # Check document presence or text-based boolean
            keyword = _extract_keyword_from_criterion(criterion_text)
            found, conf, detail = _search_text_for_keyword(all_text, keyword)
            extracted_value = "found" if found else "not found"
            confidence = conf
            layer = "deterministic"

        elif operator in ("gte", "lte", "eq", "between"):
            # Extract numeric value from text
            numeric_val = _extract_numeric_from_text(all_text, criterion_text, threshold)
            if numeric_val is not None:
                extracted_value = str(numeric_val)
                confidence = 0.85
                layer = "deterministic"
            else:
                extracted_value = "0"
                confidence = 0.40
                layer = "deterministic"

        elif operator == "eq_string":
            # Look for exact string match
            target_value = str(threshold.get("value", ""))
            if target_value.lower() in all_text.lower():
                extracted_value = target_value
                confidence = 0.95
            else:
                extracted_value = ""
                confidence = 0.70
            layer = "deterministic"

        elif operator == "semantic_match":
            # ── STAGE 2: Semantic Matching via Gemini ──
            try:
                from app.features.matching.semantic import semantic_matcher
                result_match = await semantic_matcher.compare(
                    tender_requirement=criterion_text,
                    bidder_value=all_text[:5000],  # Limit context window
                )
                extracted_value = result_match
                confidence = result_match.get("confidence", 0.0)
                layer = "semantic"
            except Exception as e:
                extracted_value = {"match": False, "confidence": 0.0, "reasoning": str(e)}
                confidence = 0.0
                layer = "semantic"

        elif operator == "modifier":
            # Conditional criteria — check if condition exists
            keyword = _extract_keyword_from_criterion(criterion_text)
            found, conf, detail = _search_text_for_keyword(all_text, keyword)
            extracted_value = "true" if found else "false"
            confidence = conf
            layer = "deterministic"

        else:
            # Fallback: try text search
            keyword = _extract_keyword_from_criterion(criterion_text)
            found, conf, detail = _search_text_for_keyword(all_text, keyword)
            extracted_value = "found" if found else "not found"
            confidence = conf
            layer = "deterministic"

        # ── STAGE 3: Normalise score using the operator ──
        normalised_score, formula = normaliser.evaluate(
            operator=operator,
            bidder_value=extracted_value,
            threshold=threshold,
            criterion_type=ctype,
        )

        # Calculate weighted score
        weight = criterion.get("weight", 0.0)
        weighted_score = (weight / 100.0) * normalised_score * 100.0

        # Route through confidence router
        routing = confidence_router.route(confidence)

        # Determine verdict string
        if normalised_score >= 0.8:
            verdict_str = "pass"
        elif normalised_score > 0.0:
            verdict_str = "partial"
        else:
            verdict_str = "fail"

        # Store verdict in DB
        verdict = Verdict(
            criterion_id=criterion_record.id,
            bidder_id=bidder_id,
            verdict=verdict_str,
            normalised_score=normalised_score,
            weighted_score=round(weighted_score, 2),
            confidence=confidence,
            layer=layer,
            auto_approved=routing["auto_approved"],
        )
        db.add(verdict)

    await db.flush()

    # Update bidder status
    bidder = await db.get(Bidder, bidder_id)
    if bidder:
        bidder.status = "scored"
        await db.flush()


def _extract_keyword_from_criterion(text: str) -> str:
    """Extract the most relevant keyword/phrase from criterion text for searching."""
    import re
    # Look for quoted terms first
    quoted = re.findall(r'"([^"]+)"', text)
    if quoted:
        return quoted[0]

    # Look for specific document types or certification names
    keywords = [
        "GST", "GSTIN", "PAN", "ISO", "BIS", "MSME", "EMD",
        "turnover", "experience", "registration", "certificate",
        "license", "licence", "accreditation", "compliance",
        "financial", "annual report", "balance sheet", "bid security",
        "earnest money", "power of attorney", "affidavit",
    ]
    text_lower = text.lower()
    for kw in keywords:
        if kw.lower() in text_lower:
            return kw

    # Fallback: use first 3 significant words
    words = [w for w in text.split() if len(w) > 3]
    return " ".join(words[:3]) if words else text[:20]


def _search_text_for_keyword(text: str, keyword: str) -> tuple:
    """Search OCR text for a keyword. Returns (found, confidence, detail)."""
    if not text or not keyword:
        return False, 0.0, "No text or keyword"

    text_lower = text.lower()
    keyword_lower = keyword.lower()

    if keyword_lower in text_lower:
        # Check for GSTIN pattern specifically
        if keyword_lower in ("gst", "gstin"):
            is_valid, conf, detail = DeterministicMatcher.validate_gstin(
                _find_gstin_in_text(text)
            )
            return is_valid, conf, detail

        # Check for PAN pattern
        if keyword_lower == "pan":
            is_valid, conf, detail = DeterministicMatcher.validate_pan(
                _find_pan_in_text(text)
            )
            return is_valid, conf, detail

        return True, 0.90, f"Keyword '{keyword}' found in document"

    return False, 0.85, f"Keyword '{keyword}' not found in document"


def _find_gstin_in_text(text: str) -> str:
    """Find a GSTIN number in text."""
    import re
    pattern = re.compile(r'[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}')
    match = pattern.search(text.upper())
    return match.group() if match else ""


def _find_pan_in_text(text: str) -> str:
    """Find a PAN number in text."""
    import re
    pattern = re.compile(r'[A-Z]{5}[0-9]{4}[A-Z]{1}')
    match = pattern.search(text.upper())
    return match.group() if match else ""


def _extract_numeric_from_text(text: str, criterion_text: str, threshold: dict) -> float:
    """Extract a numeric value from text relevant to the criterion."""
    # Use DeterministicMatcher's numeric extractor
    # First try to find the value near relevant keywords
    import re

    keyword = _extract_keyword_from_criterion(criterion_text)
    text_lower = text.lower()
    keyword_lower = keyword.lower()

    # Find text around the keyword
    idx = text_lower.find(keyword_lower)
    if idx >= 0:
        # Extract context around the keyword (200 chars before and after)
        start = max(0, idx - 200)
        end = min(len(text), idx + len(keyword) + 200)
        context = text[start:end]

        # Try to extract numeric from context
        value = DeterministicMatcher.extract_numeric_value(context)
        if value is not None:
            return value

    # Fallback: try to extract any numeric value from the whole text
    # This is less accurate but better than nothing
    value = DeterministicMatcher.extract_numeric_value(text[:2000])
    return value


@celery_app.task(name="matching.run_matching_pipeline")
def run_matching_pipeline(tender_id: str, bidder_id: str):
    """
    Run the three-stage matching pipeline for a single bidder.
    Called by the bidder_parsing task after OCR completes.
    (Celery task wrapper — delegates to async function)
    """
    import asyncio
    from app.shared.database import async_session

    async def _run():
        async with async_session() as db:
            # Load criteria
            result = await db.execute(
                select(Criterion).where(Criterion.tender_id == tender_id)
            )
            criteria = result.scalars().all()
            criteria_dicts = [
                {
                    "criterion_id": c.criterion_id,
                    "text": c.text,
                    "type": c.type,
                    "mandatory": c.mandatory,
                    "threshold_json": c.threshold_json,
                    "weight": c.weight,
                }
                for c in criteria
            ]
            await run_matching_for_bidder(db, tender_id, bidder_id, criteria_dicts)
            await db.commit()

    asyncio.run(_run())

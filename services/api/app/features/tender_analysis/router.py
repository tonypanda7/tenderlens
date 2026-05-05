"""
TenderLens — F-02 Tender Analysis Router
POST /api/v1/tender/{id}/analyse
POST /api/v1/tender/{id}/lock
"""

import hashlib
import io
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.shared.database import get_db
from app.shared.models import Tender, Criterion
from app.shared.schemas import TenderCreate, TenderResponse, CriterionUpdate
from app.features.tender_analysis.extractor import TenderCriterionExtractor

router = APIRouter()


@router.post("/create")
async def create_tender(
    tender: TenderCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new tender record."""
    new_tender = Tender(
        title=tender.title,
        description=tender.description,
        status="draft",
    )
    db.add(new_tender)
    await db.flush()

    return {"id": new_tender.id, "title": new_tender.title, "status": "draft"}
@router.get("/")
async def list_tenders(db: AsyncSession = Depends(get_db)):
    """List all tenders, ordered by newest first."""
    result = await db.execute(select(Tender).order_by(Tender.created_at.desc()))
    tenders = result.scalars().all()
    return [
        {
            "id": t.id,
            "title": t.title,
            "status": t.status,
            "created_at": t.created_at,
        }
        for t in tenders
    ]


@router.post("/{tender_id}/analyse")
async def analyse_tender(
    tender_id: str,
    file: UploadFile = File(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger Gemini 2.5 Flash to extract criteria from the tender PDF.
    Accepts an optional PDF file upload. Extracts text using TypedPdfParser,
    stores the PDF in MinIO, sends text to Gemini, and stores criteria as draft.
    """
    tender = await db.get(Tender, tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    if tender.status not in ("draft", "analysed"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot re-analyse tender in status '{tender.status}'",
        )

    # Extract text from uploaded PDF
    tender_text = ""
    print(f"DEBUG analyse: file={file}, filename={getattr(file, 'filename', None)}, size={getattr(file, 'size', None)}")
    if file and file.filename:
        pdf_bytes = await file.read()
        print(f"DEBUG analyse: read {len(pdf_bytes)} bytes from uploaded file '{file.filename}'")

        # Store the tender PDF in MinIO
        try:
            from app.shared.storage import storage_client
            minio_path = f"tenders/{tender_id}/tender_document/{file.filename}"
            storage_client.upload_file(
                file_data=pdf_bytes,
                object_name=minio_path,
                content_type=file.content_type or "application/pdf",
            )
        except Exception as e:
            print(f"DEBUG analyse: MinIO upload failed: {e}")

        # Extract text using TypedPdfParser
        from app.features.bidder_parsing.parsers import TypedPdfParser
        parser = TypedPdfParser()
        pages_data, _ = parser.parse(pdf_bytes)
        for page in pages_data:
            for block in page.get("blocks", []):
                tender_text += block.get("text", "") + "\n"
        print(f"DEBUG analyse: pdfplumber extracted {len(tender_text)} chars from {len(pages_data)} pages")

        # Fallback to PyMuPDF if pdfplumber extracted nothing or very little
        if len(tender_text.strip()) < 50:
            import fitz
            try:
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                tender_text = "\n".join(page.get_text() for page in doc)
                print(f"DEBUG analyse: PyMuPDF fallback extracted {len(tender_text)} chars")
            except Exception as e:
                print(f"DEBUG analyse: PyMuPDF fallback failed: {e}")

        if len(tender_text.strip()) < 50:
            raise HTTPException(
                status_code=400,
                detail="Could not extract text from the uploaded PDF. Please ensure you are uploading a searchable/typed PDF and not a scanned image."
            )
    else:
        print("DEBUG analyse: no file uploaded, using title/description fallback")

    if not tender_text.strip():
        # This only happens if they didn't upload a file at all
        tender_text = f"Tender Title: {tender.title}\nDescription: {tender.description or 'No description provided.'}"

    print(f"DEBUG analyse: final tender_text length = {len(tender_text)}, snippet: {tender_text[:300]}")

    extractor = TenderCriterionExtractor()
    result = await extractor.extract_criteria(tender_text, tender_id)

    if "error" in result:
        print(f"DEBUG: extractor error = {result['error']}")
        error_msg = result["error"]
        status_code = 503 if "503" in error_msg or "UNAVAILABLE" in error_msg else 500
        raise HTTPException(status_code=status_code, detail=error_msg)

    # Delete existing criteria for this tender (supports re-analysis)
    await db.execute(
        delete(Criterion).where(Criterion.tender_id == tender_id)
    )

    # Store extracted criteria in DB
    for c in result["criteria"]:
        criterion = Criterion(
            tender_id=tender_id,
            criterion_id=c["criterion_id"],
            text=c["text"],
            type=c["type"],
            mandatory=c["mandatory"],
            threshold_json=c.get("threshold"),
            weight=c["weight"],
            source_section=c.get("source_section"),
            source_page=c.get("source_page"),
            ambiguous=c.get("ambiguous", False),
            ambiguity_note=c.get("ambiguity_note"),
            status="draft",
            prompt_version=result["prompt_version"],
        )
        db.add(criterion)

    tender.status = "analysed"
    tender.prompt_version = result["prompt_version"]
    await db.flush()

    return {
        "tender_id": tender_id,
        "status": "analysed",
        "criteria_count": len(result["criteria"]),
        "prompt_version": result["prompt_version"],
    }


@router.put("/{tender_id}/criteria/{criterion_id}")
async def update_criterion(
    tender_id: str,
    criterion_id: str,
    update: CriterionUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Officer can edit criteria before locking."""
    result = await db.execute(
        select(Criterion).where(
            Criterion.tender_id == tender_id,
            Criterion.criterion_id == criterion_id,
            Criterion.status == "draft",
        )
    )
    criterion = result.scalar_one_or_none()

    if not criterion:
        raise HTTPException(status_code=404, detail="Criterion not found or already locked")

    if update.text is not None:
        criterion.text = update.text
    if update.type is not None:
        criterion.type = update.type
    if update.mandatory is not None:
        criterion.mandatory = update.mandatory
    if update.weight is not None:
        criterion.weight = update.weight
    if update.threshold is not None:
        criterion.threshold_json = update.threshold.model_dump()

    return {"message": "Criterion updated", "criterion_id": criterion_id}


@router.post("/{tender_id}/lock")
async def lock_tender_criteria(
    tender_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Lock the criterion registry. No evaluation starts until lock_hash exists.
    lock_hash = SHA-256 of sorted criterion IDs + thresholds.
    """
    tender = await db.get(Tender, tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    if tender.status != "analysed":
        raise HTTPException(
            status_code=400,
            detail=f"Can only lock from 'analysed' status. Current: '{tender.status}'",
        )

    # Get all criteria for this tender
    result = await db.execute(
        select(Criterion).where(Criterion.tender_id == tender_id)
    )
    criteria = result.scalars().all()

    if not criteria:
        raise HTTPException(status_code=400, detail="No criteria to lock")

    # Compute lock_hash
    criterion_ids = sorted([c.criterion_id for c in criteria])
    thresholds = sorted([json.dumps(c.threshold_json or {}) for c in criteria])
    combined = "|".join(criterion_ids + thresholds)
    lock_hash = hashlib.sha256(combined.encode("utf-8")).hexdigest()

    # Lock all criteria
    for c in criteria:
        c.status = "locked"

    tender.lock_hash = lock_hash
    tender.status = "locked"

    return {
        "tender_id": tender_id,
        "status": "locked",
        "lock_hash": lock_hash,
        "criteria_locked": len(criteria),
    }


@router.get("/{tender_id}")
async def get_tender(
    tender_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get tender details with criteria."""
    tender = await db.get(Tender, tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    result = await db.execute(
        select(Criterion).where(Criterion.tender_id == tender_id)
    )
    criteria = result.scalars().all()

    return {
        "id": tender.id,
        "title": tender.title,
        "description": tender.description,
        "status": tender.status,
        "lock_hash": tender.lock_hash,
        "prompt_version": tender.prompt_version,
        "criteria": [
            {
                "criterion_id": c.criterion_id,
                "text": c.text,
                "type": c.type,
                "mandatory": c.mandatory,
                "threshold": c.threshold_json,
                "weight": c.weight,
                "source_section": c.source_section,
                "source_page": c.source_page,
                "ambiguous": c.ambiguous,
                "ambiguity_note": c.ambiguity_note,
                "status": c.status,
            }
            for c in criteria
        ],
    }


@router.get("/{tender_id}/bidders")
async def list_tender_bidders(
    tender_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List all bidders for a tender with their file counts and status."""
    from app.shared.models import Bidder, IngestFile
    from sqlalchemy import func

    tender = await db.get(Tender, tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    # Get bidders with file counts
    result = await db.execute(
        select(
            Bidder,
            func.count(IngestFile.id).label("files_count")
        )
        .outerjoin(IngestFile, IngestFile.bidder_id == Bidder.id)
        .where(Bidder.tender_id == tender_id)
        .group_by(Bidder.id)
        .order_by(Bidder.created_at.desc())
    )
    rows = result.all()

    return {
        "tender_id": tender_id,
        "bidders": [
            {
                "id": bidder.id,
                "name": bidder.name,
                "pseudonym_id": bidder.pseudonym_id,
                "status": bidder.status,
                "files_count": files_count,
                "created_at": bidder.created_at.isoformat() if bidder.created_at else None,
            }
            for bidder, files_count in rows
        ],
    }


@router.post("/{tender_id}/evaluate")
async def evaluate_tender(
    tender_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger the full evaluation pipeline for all bidders in a tender.
    1. Ensures criteria are locked
    2. Runs matching pipeline for each bidder
    3. Scores and ranks all bidders
    4. Returns ranking summary
    """
    from app.shared.models import Bidder, Verdict, BidderScore
    from app.features.matching.tasks import run_matching_for_bidder
    from app.features.scoring.engine import ScoringEngine
    from app.features.scoring.rationale import RationaleGenerator

    tender = await db.get(Tender, tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    # Auto-lock if still in analysed state
    if tender.status == "analysed":
        result = await db.execute(
            select(Criterion).where(Criterion.tender_id == tender_id)
        )
        criteria_list = result.scalars().all()
        if not criteria_list:
            raise HTTPException(status_code=400, detail="No criteria found. Analyse tender first.")

        criterion_ids = sorted([c.criterion_id for c in criteria_list])
        thresholds = sorted([json.dumps(c.threshold_json or {}) for c in criteria_list])
        combined = "|".join(criterion_ids + thresholds)
        lock_hash = hashlib.sha256(combined.encode("utf-8")).hexdigest()

        for c in criteria_list:
            c.status = "locked"
        tender.lock_hash = lock_hash
        tender.status = "locked"
        await db.flush()

    # Get criteria
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
            "source_section": c.source_section,
            "source_page": c.source_page,
        }
        for c in criteria
    ]

    # Get all bidders
    result = await db.execute(
        select(Bidder).where(Bidder.tender_id == tender_id)
    )
    bidders = result.scalars().all()

    if not bidders:
        raise HTTPException(status_code=400, detail="No bidders found. Upload bidder documents first.")

    # Run matching for each bidder (synchronous for now)
    for bidder in bidders:
        await run_matching_for_bidder(db, tender_id, bidder.id, criteria_dicts)

    # Score all bidders
    scoring_engine = ScoringEngine()
    scored_bidders = []

    # Build a reverse map: criterion DB id → criterion_id (e.g. "C1")
    criterion_id_map = {}
    for c in criteria:
        criterion_id_map[c.id] = c.criterion_id

    for bidder in bidders:
        # Get verdicts for this bidder
        from sqlalchemy.orm import joinedload
        result = await db.execute(
            select(Verdict)
            .options(joinedload(Verdict.criterion))
            .where(Verdict.bidder_id == bidder.id)
        )
        verdicts = result.scalars().unique().all()

        verdict_dicts = [
            {
                "criterion_id": criterion_id_map.get(v.criterion_id, "unknown"),
                "verdict": v.verdict,
                "normalised_score": v.normalised_score,
                "weighted_score": v.weighted_score,
                "confidence": v.confidence,
                "layer": v.layer,
                "auto_approved": v.auto_approved,
                "extracted_value": None,
            }
            for v in verdicts
        ]

        scored = scoring_engine.score_bidder(
            bidder_id=bidder.id,
            bidder_name=bidder.name,
            verdicts=verdict_dicts,
            criteria=criteria_dicts,
        )
        scored_bidders.append(scored)

    # Rank
    ranking_result = scoring_engine.rank_bidders(scored_bidders)

    # Generate rationales
    try:
        rationale_gen = RationaleGenerator()
        ranking_result["rankings"] = await rationale_gen.generate_rationales(
            ranking_result["rankings"], tender.title
        )
    except Exception as e:
        print(f"Rationale generation failed: {e}")

    # Save scores to DB
    for bidder_data in ranking_result["rankings"] + ranking_result["disqualified"]:
        # Delete existing score
        existing = await db.execute(
            select(BidderScore).where(
                BidderScore.bidder_id == bidder_data["bidder_id"],
                BidderScore.tender_id == tender_id,
            )
        )
        old = existing.scalar_one_or_none()
        if old:
            await db.delete(old)
            await db.flush()

        score_record = BidderScore(
            bidder_id=bidder_data["bidder_id"],
            tender_id=tender_id,
            rank=bidder_data.get("rank"),
            final_score=bidder_data.get("final_score", 0.0),
            eligible=bidder_data.get("eligible", False),
            disqualified=bidder_data.get("disqualified", False),
            disqualify_reason=bidder_data.get("disqualify_reason"),
            criterion_scores_json=bidder_data.get("criterion_scores"),
            rationale=bidder_data.get("rationale"),
        )
        db.add(score_record)

    tender.status = "evaluated"
    await db.flush()

    return {
        "tender_id": tender_id,
        "status": "evaluated",
        "total_bidders": ranking_result["total_bidders"],
        "eligible_count": ranking_result["eligible_count"],
        "disqualified_count": ranking_result["disqualified_count"],
        "message": f"Evaluation complete. {ranking_result['eligible_count']} eligible, {ranking_result['disqualified_count']} disqualified.",
    }

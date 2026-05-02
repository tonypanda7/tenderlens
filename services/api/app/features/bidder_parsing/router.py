"""
TenderLens — F-03 Bidder Parsing Router
POST /api/v1/bidder/{bidder_id}/parse
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.shared.database import get_db
from app.shared.models import Bidder, IngestFile

router = APIRouter()


@router.post("/{bidder_id}/parse")
async def trigger_bidder_parsing(
    bidder_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger document parsing for a bidder.
    Routes each file to the appropriate parser based on format_detected.
    """
    bidder = await db.get(Bidder, bidder_id)
    if not bidder:
        raise HTTPException(status_code=404, detail="Bidder not found")

    result = await db.execute(
        select(IngestFile).where(IngestFile.bidder_id == bidder_id)
    )
    files = result.scalars().all()

    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded for this bidder")

    # Trigger async parsing via Celery
    from app.features.bidder_parsing.tasks import parse_bidder_documents
    task = parse_bidder_documents.delay(bidder_id)

    return {
        "bidder_id": bidder_id,
        "files_count": len(files),
        "task_id": task.id,
        "status": "parsing_started",
    }


@router.get("/{bidder_id}/blocks")
async def get_bidder_ocr_blocks(
    bidder_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get all OCR blocks extracted for a bidder."""
    from app.shared.models import OcrBlock

    bidder = await db.get(Bidder, bidder_id)
    if not bidder:
        raise HTTPException(status_code=404, detail="Bidder not found")

    result = await db.execute(
        select(IngestFile).where(IngestFile.bidder_id == bidder_id)
    )
    files = result.scalars().all()
    file_ids = [f.id for f in files]

    blocks_result = await db.execute(
        select(OcrBlock).where(OcrBlock.file_id.in_(file_ids)).order_by(OcrBlock.page_number)
    )
    blocks = blocks_result.scalars().all()

    return {
        "bidder_id": bidder_id,
        "total_blocks": len(blocks),
        "blocks": [
            {
                "block_id": b.block_id,
                "text": b.text,
                "bbox": b.bbox,
                "confidence": b.confidence,
                "type": b.type,
                "page_number": b.page_number,
                "file_id": b.file_id,
            }
            for b in blocks
        ],
    }

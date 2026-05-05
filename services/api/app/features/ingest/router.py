"""
TenderLens — F-01 Document Ingest Router
POST /api/v1/ingest/upload (multipart/form-data)

Accepts up to 50 files per bundle. Validates MIME type. Streams to MinIO.
Computes SHA-256. Returns file manifest JSON. Triggers async Celery processing.
Duplicate uploads deduplicated by SHA-256.
"""

import hashlib
import uuid
from typing import List, Optional

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.shared.database import get_db
from app.shared.models import IngestFile, Bidder, Tender
from app.shared.schemas import IngestResponse, FileManifestItem

router = APIRouter()

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/tiff",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

MAX_FILES_PER_BUNDLE = 50


def detect_format(mime_type: str, content: bytes) -> str:
    """Detect document format from MIME type."""
    if mime_type == "application/pdf":
        # Check if it's a typed or scanned PDF
        # Simple heuristic: if we can extract substantial text, it's typed
        return "typed_pdf"  # Will be refined during parsing
    elif mime_type in ("image/jpeg", "image/png"):
        return "photo"
    elif mime_type == "image/tiff":
        return "scanned"
    elif "wordprocessingml" in mime_type:
        return "docx"
    return "unknown"


@router.post("/upload", response_model=IngestResponse)
async def upload_documents(
    tender_id: str = Form(...),
    bidder_name: str = Form(...),
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload bidder documents for a tender.
    - Validates MIME types
    - Computes SHA-256 for deduplication
    - Stores in MinIO
    - Returns file manifest
    - Triggers async Celery processing
    """
    if len(files) > MAX_FILES_PER_BUNDLE:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_FILES_PER_BUNDLE} files per upload. Got {len(files)}.",
        )

    # Verify tender exists
    tender = await db.get(Tender, tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail=f"Tender {tender_id} not found")

    # Create or get bidder
    pseudonym_id = f"b_{uuid.uuid4().hex[:6]}"
    bidder = Bidder(
        tender_id=tender_id,
        name=bidder_name,
        pseudonym_id=pseudonym_id,
        status="pending",
    )
    db.add(bidder)
    await db.flush()

    manifest: List[FileManifestItem] = []

    for upload_file in files:
        # Validate MIME type
        if upload_file.content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {upload_file.content_type}. "
                       f"Allowed: {', '.join(ALLOWED_MIME_TYPES)}",
            )

        # Read content and compute SHA-256
        content = await upload_file.read()
        sha256 = hashlib.sha256(content).hexdigest()

        # Check for duplicate by SHA-256
        existing = await db.execute(
            select(IngestFile).where(IngestFile.sha256 == sha256)
        )
        if existing.scalar_one_or_none():
            continue  # Skip duplicate

        # Detect format
        format_detected = detect_format(upload_file.content_type, content)

        # MinIO path
        minio_path = f"tenders/{tender_id}/bidders/{bidder.id}/{sha256}/{upload_file.filename}"

        # Upload to MinIO via minio client
        from app.shared.storage import storage_client
        storage_client.upload_file(
            file_data=content,
            object_name=minio_path,
            content_type=upload_file.content_type
        )

        # Create DB record
        file_record = IngestFile(
            bidder_id=bidder.id,
            minio_path=minio_path,
            sha256=sha256,
            mime_type=upload_file.content_type,
            format_detected=format_detected,
            original_filename=upload_file.filename,
        )
        db.add(file_record)
        await db.flush()

        manifest.append(FileManifestItem(
            file_id=file_record.id,
            original_filename=upload_file.filename or "unknown",
            sha256=sha256,
            mime_type=upload_file.content_type,
            format_detected=format_detected,
            minio_path=minio_path,
        ))

    # Trigger Celery task for async document processing
    from app.features.bidder_parsing.tasks import parse_bidder_documents
    parse_bidder_documents.delay(bidder.id)

    return IngestResponse(
        bidder_id=bidder.id,
        tender_id=tender_id,
        files=manifest,
        message=f"Uploaded {len(manifest)} files for bidder '{bidder_name}'. Processing started.",
    )

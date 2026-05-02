"""
TenderLens — F-07 Audit Log Router
GET  /api/v1/audit/{tender_id}
POST /api/v1/audit/{tender_id}/export

Every verdict, reviewer action, and score event writes one append-only row.
Each row has SHA-256 chain link. Tampering invalidates all subsequent hashes.
"""

import json
import hashlib
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.shared.database import get_db
from app.shared.models import AuditLog, Tender
from app.features.matching.engine import AuditHashChain

router = APIRouter()


async def write_audit_entry(
    db: AsyncSession,
    event_type: str,
    payload: dict,
) -> AuditLog:
    """
    Write a single append-only audit log entry with hash chain.
    Called by all features when recording auditable events.
    """
    # Get the most recent entry for the prev_hash
    result = await db.execute(
        select(AuditLog).order_by(desc(AuditLog.ts)).limit(1)
    )
    last_entry = result.scalar_one_or_none()
    prev_hash = last_entry.this_hash if last_entry else None

    # Generate entry ID
    import uuid
    entry_id = str(uuid.uuid4())

    # Compute hash chain
    payload_str = json.dumps(payload, sort_keys=True, default=str)
    this_hash = AuditHashChain.compute_hash(prev_hash, entry_id, payload_str)

    entry = AuditLog(
        id=entry_id,
        event_type=event_type,
        payload=payload,
        prev_hash=prev_hash,
        this_hash=this_hash,
    )
    db.add(entry)
    await db.flush()
    return entry


@router.get("/{tender_id}")
async def get_audit_log(
    tender_id: str,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """Get audit log entries for a tender."""
    tender = await db.get(Tender, tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    # Query audit entries related to this tender
    result = await db.execute(
        select(AuditLog)
        .order_by(AuditLog.ts)
        .limit(limit)
        .offset(offset)
    )
    entries = result.scalars().all()

    # Filter entries related to this tender_id (in payload)
    tender_entries = [
        e for e in entries
        if e.payload and e.payload.get("tender_id") == tender_id
    ]

    return {
        "tender_id": tender_id,
        "total": len(tender_entries),
        "entries": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "payload": e.payload,
                "prev_hash": e.prev_hash,
                "this_hash": e.this_hash,
                "ts": e.ts.isoformat() if e.ts else None,
            }
            for e in tender_entries
        ],
    }


@router.get("/{tender_id}/verify")
async def verify_audit_chain(
    tender_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Verify the integrity of the audit hash chain for a tender."""
    result = await db.execute(
        select(AuditLog).order_by(AuditLog.ts)
    )
    entries = result.scalars().all()

    entries_data = [
        {
            "id": e.id,
            "payload": e.payload,
            "prev_hash": e.prev_hash,
            "this_hash": e.this_hash,
        }
        for e in entries
    ]

    is_valid, first_invalid = AuditHashChain.verify_chain(entries_data)

    return {
        "tender_id": tender_id,
        "chain_valid": is_valid,
        "total_entries": len(entries_data),
        "first_invalid_entry": first_invalid,
    }


@router.post("/{tender_id}/export")
async def export_signed_pdf(
    tender_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate signed PDF export for a tender.
    Includes: ranked table, per-bidder rationale, disqualified list, hash chain.
    Target: complete in under 30 seconds.
    """
    tender = await db.get(Tender, tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    # TODO: Generate PDF with:
    # 1. Full ranked table
    # 2. Per-bidder rationale
    # 3. Disqualified list with reasons
    # 4. Hash chain verification block
    # 5. DSC signature (self-signed for hackathon)

    return {
        "tender_id": tender_id,
        "status": "export_started",
        "message": "PDF export initiated — implement with ReportLab or WeasyPrint",
    }

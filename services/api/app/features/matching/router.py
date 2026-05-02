"""
TenderLens — F-04 Matching Router
Internal Celery task — not a REST endpoint (as per PRD).
Exposes a status endpoint for the frontend to poll.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database import get_db

router = APIRouter()


@router.get("/{tender_id}/matching/status")
async def get_matching_status(
    tender_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get the current matching status for a tender's bidders."""
    # TODO: Query verdicts table for progress
    return {
        "tender_id": tender_id,
        "status": "pending",
        "message": "Matching engine status — implement with Celery task tracking",
    }

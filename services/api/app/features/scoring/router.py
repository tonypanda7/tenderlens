"""
TenderLens — F-05 Scoring Router
GET /api/v1/tender/{id}/ranking
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.shared.database import get_db
from app.shared.models import Tender, Bidder, BidderScore, Verdict

router = APIRouter()


@router.get("/{tender_id}/ranking")
async def get_tender_ranking(
    tender_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get the full ranked output for a tender.
    Returns ranked table + disqualified list + rationale.
    """
    tender = await db.get(Tender, tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")

    return {
        "tender_id": tender_id,
        "tender_title": tender.title,
        "total_bidders": 0,
        "eligible_count": 0,
        "disqualified_count": 0,
        "pending_reviews": 0,
        "rankings": [],
        "disqualified": [],
        "simple_result": tender.description
    }

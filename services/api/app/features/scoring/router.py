"""
TenderLens — F-05 Scoring Router
GET /api/v1/tender/{id}/ranking
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.database import get_db
from app.shared.schemas import RankedOutputResponse

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
    # TODO: Query bidder_scores table, join with bidders
    # Return RankedOutputResponse
    return {
        "tender_id": tender_id,
        "total_bidders": 0,
        "eligible_count": 0,
        "disqualified_count": 0,
        "pending_reviews": 0,
        "rankings": [],
        "disqualified": [],
        "message": "Scoring endpoint ready — implement DB query",
    }

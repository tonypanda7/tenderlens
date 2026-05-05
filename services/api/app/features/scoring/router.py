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

    # Query bidder_scores table
    result = await db.execute(
        select(BidderScore)
        .where(BidderScore.tender_id == tender_id)
        .order_by(BidderScore.rank.asc().nullslast(), BidderScore.final_score.desc())
    )
    scores = result.scalars().all()

    if not scores:
        # No scores yet — return empty but valid response
        # Count bidders to show useful stats
        bidder_result = await db.execute(
            select(Bidder).where(Bidder.tender_id == tender_id)
        )
        bidder_count = len(bidder_result.scalars().all())

        return {
            "tender_id": tender_id,
            "tender_title": tender.title,
            "total_bidders": bidder_count,
            "eligible_count": 0,
            "disqualified_count": 0,
            "pending_reviews": 0,
            "rankings": [],
            "disqualified": [],
        }

    # Separate eligible and disqualified
    rankings = []
    disqualified = []

    for score in scores:
        # Get bidder name
        bidder = await db.get(Bidder, score.bidder_id)
        bidder_name = bidder.name if bidder else "Unknown"

        entry = {
            "bidder_id": score.bidder_id,
            "bidder_name": bidder_name,
            "tender_id": tender_id,
            "rank": score.rank,
            "final_score": score.final_score,
            "eligible": score.eligible,
            "disqualified": score.disqualified,
            "disqualify_reason": score.disqualify_reason,
            "criterion_scores": score.criterion_scores_json or [],
            "rationale": score.rationale,
            "computed_at": score.computed_at.isoformat() if score.computed_at else None,
        }

        if score.disqualified:
            disqualified.append(entry)
        else:
            rankings.append(entry)

    # Count pending reviews (verdicts with low confidence that haven't been reviewed)
    pending_count = 0
    try:
        from app.shared.models import ReviewerQueueItem
        pending_result = await db.execute(
            select(ReviewerQueueItem).where(ReviewerQueueItem.status == "pending")
        )
        pending_count = len(pending_result.scalars().all())
    except Exception:
        pass

    return {
        "tender_id": tender_id,
        "tender_title": tender.title,
        "total_bidders": len(scores),
        "eligible_count": len(rankings),
        "disqualified_count": len(disqualified),
        "pending_reviews": pending_count,
        "rankings": rankings,
        "disqualified": disqualified,
    }

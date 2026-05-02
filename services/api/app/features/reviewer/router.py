"""
TenderLens — F-06 Reviewer Workflow Router
GET  /api/v1/reviewer/queue
POST /api/v1/reviewer/{id}/decide

Queue ordered by: escalated first → tender deadline → confidence ascending.
No bulk-approve. Re-opening creates a new row — original never mutated.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, asc, case

from app.shared.database import get_db
from app.shared.models import ReviewerQueueItem, ReviewerAction, Verdict
from app.shared.schemas import ReviewerQueueItemResponse, ReviewerDecision

router = APIRouter()


@router.get("/queue")
async def get_reviewer_queue(
    status: str = "pending",
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """
    Get the reviewer queue, ordered by:
      1. Escalated items first
      2. Then by confidence ascending (lowest confidence = most urgent)
      3. Then by priority descending
    """
    # Priority ordering: escalated first, then pending
    priority_order = case(
        (ReviewerQueueItem.status == "escalated", 0),
        (ReviewerQueueItem.status == "pending", 1),
        (ReviewerQueueItem.status == "in_progress", 2),
        else_=3,
    )

    result = await db.execute(
        select(ReviewerQueueItem)
        .where(ReviewerQueueItem.status.in_(["pending", "escalated", "in_progress"]))
        .order_by(priority_order, asc(ReviewerQueueItem.priority), desc(ReviewerQueueItem.created_at))
        .limit(limit)
        .offset(offset)
    )
    items = result.scalars().all()

    return {
        "total": len(items),
        "items": [
            {
                "id": item.id,
                "verdict_id": item.verdict_id,
                "flag_reason": item.flag_reason,
                "status": item.status,
                "priority": item.priority,
                "assigned_to": item.assigned_to,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in items
        ],
    }


@router.post("/{queue_item_id}/decide")
async def decide_queue_item(
    queue_item_id: str,
    decision: ReviewerDecision,
    db: AsyncSession = Depends(get_db),
):
    """
    Record a reviewer decision for a queue item.
    Decision requires mandatory typed reason — enforced by NOT NULL DB constraint.
    No bulk-approve allowed.
    """
    item = await db.get(ReviewerQueueItem, queue_item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Queue item not found")

    if item.status == "decided":
        raise HTTPException(
            status_code=400,
            detail="Item already decided. To re-open, create a new review item.",
        )

    # Validate action
    valid_actions = {"approve", "reject", "override", "escalate"}
    if decision.action not in valid_actions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action '{decision.action}'. Must be one of: {valid_actions}",
        )

    # Create reviewer action (append-only — original never mutated)
    action = ReviewerAction(
        queue_item_id=queue_item_id,
        action=decision.action,
        corrected_value=decision.corrected_value,
        reason=decision.reason,
        actor_id="officer",  # TODO: Get from auth context
        is_training_candidate=decision.action == "override",
    )
    db.add(action)

    # Update queue item status
    if decision.action == "escalate":
        item.status = "escalated"
    else:
        item.status = "decided"

    await db.flush()

    return {
        "queue_item_id": queue_item_id,
        "action": decision.action,
        "status": item.status,
        "message": f"Decision recorded: {decision.action}",
    }


@router.get("/{queue_item_id}")
async def get_queue_item_detail(
    queue_item_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get full detail for a reviewer queue item including verdict and actions."""
    item = await db.get(ReviewerQueueItem, queue_item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Queue item not found")

    # Get the verdict
    verdict = await db.get(Verdict, item.verdict_id) if item.verdict_id else None

    # Get all actions for this item
    actions_result = await db.execute(
        select(ReviewerAction)
        .where(ReviewerAction.queue_item_id == queue_item_id)
        .order_by(ReviewerAction.ts)
    )
    actions = actions_result.scalars().all()

    return {
        "id": item.id,
        "status": item.status,
        "flag_reason": item.flag_reason,
        "priority": item.priority,
        "verdict": {
            "id": verdict.id,
            "verdict": verdict.verdict,
            "confidence": verdict.confidence,
            "layer": verdict.layer,
            "normalised_score": verdict.normalised_score,
        } if verdict else None,
        "actions": [
            {
                "action": a.action,
                "corrected_value": a.corrected_value,
                "reason": a.reason,
                "actor_id": a.actor_id,
                "ts": a.ts.isoformat() if a.ts else None,
            }
            for a in actions
        ],
    }

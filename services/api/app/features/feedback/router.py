"""
TenderLens — F-08 Feedback Loop Router
Nightly Celery beat job — tags reviewer overrides for retraining.

Retraining triggers:
  OCR corrections >= 200 → fine-tune OCR model
  Few-shot pool >= 50 new examples → update Gemini prompt
  New OCR model promoted only if val CER improves by >= 2%
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.shared.database import get_db
from app.shared.models import ReviewerAction

router = APIRouter()


@router.get("/stats")
async def get_feedback_stats(
    db: AsyncSession = Depends(get_db),
):
    """Get feedback loop statistics — correction counts by type."""
    # Count total training candidates
    total_result = await db.execute(
        select(func.count(ReviewerAction.id))
        .where(ReviewerAction.is_training_candidate == True)
    )
    total_candidates = total_result.scalar() or 0

    # Count overrides (OCR corrections vs semantic mismatches)
    override_result = await db.execute(
        select(func.count(ReviewerAction.id))
        .where(
            ReviewerAction.is_training_candidate == True,
            ReviewerAction.action == "override",
        )
    )
    override_count = override_result.scalar() or 0

    return {
        "total_training_candidates": total_candidates,
        "ocr_corrections": override_count,
        "semantic_mismatches": total_candidates - override_count,
        "ocr_retrain_threshold": 200,
        "ocr_retrain_ready": override_count >= 200,
        "fewshot_update_threshold": 50,
        "fewshot_update_ready": (total_candidates - override_count) >= 50,
    }

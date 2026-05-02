"""
TenderLens — F-04 Matching Celery Tasks
"""

from app.celery_app import celery_app


@celery_app.task(name="matching.run_matching_pipeline")
def run_matching_pipeline(tender_id: str, bidder_id: str):
    """
    Run the three-stage matching pipeline for a single bidder.
    Called by the bidder_parsing task after OCR completes.

    Stage 1: Deterministic pre-filter (GSTIN, dates, doc presence)
    Stage 2: Gemini semantic matching (label resolution)
    Stage 3: Computation (averages, sums, counts)
    """
    # TODO: Implement full pipeline orchestration
    # 1. Load criteria from DB (locked registry)
    # 2. Load bidder's OCR blocks from DB
    # 3. Run DeterministicMatcher checks
    # 4. Run SemanticMatcher for remaining criteria
    # 5. Run ComputationMatcher for numeric criteria
    # 6. Route results through ConfidenceRouter
    # 7. Store verdicts in DB
    # 8. Trigger scoring if all bidders complete
    pass

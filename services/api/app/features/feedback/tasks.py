"""
TenderLens — F-08 Feedback Loop Celery Tasks
Nightly job — counts corrections and triggers retraining when thresholds met.
"""

from app.celery_app import celery_app


@celery_app.task(name="feedback.nightly_feedback_check")
def nightly_feedback_check():
    """
    Nightly Celery beat job:
      1. Count OCR corrections tagged is_training_candidate=true
      2. Count semantic mismatches
      3. If OCR corrections >= 200 → trigger OCR fine-tune queue
      4. If few-shot pool >= 50 → update Gemini prompt
      5. New OCR model promoted only if val CER improves by >= 2%
    """
    # TODO: Implement full feedback loop
    # 1. Query reviewer_actions WHERE is_training_candidate = true
    # 2. Categorise: OCR correction vs semantic mismatch
    # 3. Check thresholds
    # 4. Trigger retraining or prompt update
    pass

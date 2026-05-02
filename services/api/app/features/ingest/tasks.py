"""
TenderLens — F-01 Ingest Celery Tasks
"""

from app.celery_app import celery_app


@celery_app.task(name="ingest.process_uploaded_files")
def process_uploaded_files(bidder_id: str):
    """
    Process uploaded files for a bidder:
    1. Upload to MinIO
    2. Trigger format-specific parsing
    """
    # TODO: Implement MinIO upload + parsing trigger
    pass

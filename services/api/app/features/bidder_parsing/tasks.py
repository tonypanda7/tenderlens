"""
TenderLens — F-03 Bidder Parsing Celery Tasks
"""

from app.celery_app import celery_app


@celery_app.task(name="bidder_parsing.parse_bidder_documents")
def parse_bidder_documents(bidder_id: str):
    """
    Parse all documents for a bidder.

    Flow per file:
      1. Detect format (typed_pdf | scanned | photo | docx)
      2. Route to appropriate parser
      3. For scanned/photo: preprocess with OpenCV → send to OCR service
      4. Store OCR blocks in DB
      5. Flag low-confidence blocks (< 0.60) for reviewer queue
      6. When all files done: trigger matching pipeline
    """
    # TODO: Implement full parsing pipeline
    # 1. Load files from DB
    # 2. Download from MinIO
    # 3. Route: typed_pdf → TypedPdfParser, scanned → ScannedPdfParser + OCR,
    #           photo → PhotoParser + OCR, docx → DocxParser
    # 4. Store blocks in ocr_blocks table
    # 5. Trigger matching.run_matching_pipeline.delay(tender_id, bidder_id)
    pass

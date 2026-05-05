"""
TenderLens — F-03 Bidder Parsing Celery Tasks
"""

import asyncio
from sqlalchemy import select

from app.celery_app import celery_app
from app.shared.database import async_session
from app.shared.models import Bidder, IngestFile, OcrBlock
from app.shared.storage import storage_client
from app.features.bidder_parsing.parsers import TypedPdfParser, ScannedPdfParser, PhotoParser, DocxParser
from app.features.bidder_parsing.ocr_client import ocr_client
from app.features.matching.tasks import run_matching_pipeline


async def _async_parse_bidder_documents(bidder_id: str):
    async with async_session() as db:
        bidder = await db.get(Bidder, bidder_id)
        if not bidder:
            return

        # Update status to parsing
        bidder.status = "parsing"
        await db.commit()

        result = await db.execute(select(IngestFile).where(IngestFile.bidder_id == bidder_id))
        files = result.scalars().all()

        tender_id = bidder.tender_id

        for f in files:
            file_bytes = storage_client.download_file(f.minio_path)
            format_detected = f.format_detected
            blocks_to_save = []

            if format_detected == "typed_pdf":
                parser = TypedPdfParser()
                pages_data, needs_ocr = parser.parse(file_bytes)
                
                if needs_ocr:
                    # Fall back to scanned parser
                    parser = ScannedPdfParser()
                    images = parser.extract_page_images(file_bytes)
                    ocr_reqs = [
                        {
                            "image_bytes": img["image_bytes"],
                            "doc_type": "scanned",
                            "bidder_id": bidder_id,
                            "page_number": img["page_number"],
                            "file_id": f.id
                        } for img in images
                    ]
                    ocr_responses = await ocr_client.extract_batch(ocr_reqs)
                    for resp in ocr_responses:
                        if not isinstance(resp, Exception):
                            for b in resp.blocks:
                                blocks_to_save.append(b.dict() | {"page_number": resp.page_number})
                else:
                    for page in pages_data:
                        for b in page["blocks"]:
                            blocks_to_save.append(b)

            elif format_detected == "scanned":
                parser = ScannedPdfParser()
                images = parser.extract_page_images(file_bytes)
                ocr_reqs = [
                    {
                        "image_bytes": img["image_bytes"],
                        "doc_type": "scanned",
                        "bidder_id": bidder_id,
                        "page_number": img["page_number"],
                        "file_id": f.id
                    } for img in images
                ]
                ocr_responses = await ocr_client.extract_batch(ocr_reqs)
                for resp in ocr_responses:
                    if not isinstance(resp, Exception):
                        for b in resp.blocks:
                            blocks_to_save.append(b.dict() | {"page_number": resp.page_number})
                            
            elif format_detected == "photo":
                parser = PhotoParser()
                processed_bytes = parser.prepare(file_bytes)
                resp = await ocr_client.extract(
                    image_bytes=processed_bytes,
                    doc_type="photo",
                    bidder_id=bidder_id,
                    page_number=0,
                    file_id=f.id
                )
                for b in resp.blocks:
                    blocks_to_save.append(b.dict() | {"page_number": resp.page_number})
                    
            elif format_detected == "docx" or format_detected == "unknown":
                parser = DocxParser()
                blocks = parser.parse(file_bytes)
                blocks_to_save.extend(blocks)
                    
            # Save blocks to DB
            for b_data in blocks_to_save:
                block = OcrBlock(
                    file_id=f.id,
                    block_id=b_data["block_id"],
                    text=b_data["text"],
                    bbox=b_data.get("bbox"),
                    confidence=b_data.get("confidence", 0.0),
                    type=b_data.get("type", "text"),
                    page_number=b_data.get("page_number", 0)
                )
                db.add(block)
                
            await db.flush()

        bidder.status = "parsed"
        await db.commit()

        # Trigger next stage
        run_matching_pipeline.delay(tender_id, bidder_id)


@celery_app.task(name="bidder_parsing.parse_bidder_documents")
def parse_bidder_documents(bidder_id: str):
    """
    Parse all documents for a bidder.
    """
    asyncio.run(_async_parse_bidder_documents(bidder_id))

"""
TenderLens — F-03 OCR Client
Calls the local OCR service at http://ocr-service:8001/extract.
Internal network only — no document data leaves the server boundary.
"""

import httpx
from typing import Dict, Any, Optional, List

from app.config import settings
from app.shared.schemas import OcrBlockSchema, OcrPageResponse


class OcrClient:
    """
    HTTP client for the local OCR service container.
    Contract: POST http://ocr-service:8001/extract (multipart/form-data)

    Fields:
        image      : bytes  — raw image (PNG, JPEG, single-page TIFF)
        doc_type   : string — scan | photo | typed_pdf
        bidder_id  : string — internal ID only, no real name
        page_number: int    — page index within original document
    """

    def __init__(self):
        self.base_url = settings.ocr_service_url
        self.timeout = httpx.Timeout(60.0, connect=10.0)

    async def extract(
        self,
        image_bytes: bytes,
        doc_type: str,
        bidder_id: str,
        page_number: int,
        file_id: str,
    ) -> OcrPageResponse:
        """
        Send a single page image to the OCR service.
        Returns structured OCR blocks with confidence scores.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/extract",
                    files={"image": ("page.png", image_bytes, "image/png")},
                    data={
                        "doc_type": doc_type,
                        "bidder_id": bidder_id,
                        "page_number": str(page_number),
                    },
                    headers={
                        "X-API-Key": settings.ocr_api_key,
                    } if settings.ocr_api_key else {},
                )
                response.raise_for_status()
                data = response.json()

                blocks = [
                    OcrBlockSchema(
                        block_id=b.get("block_id", f"blk_{i:04d}"),
                        text=b.get("text", ""),
                        bbox=b.get("bbox"),
                        confidence=b.get("confidence", 0.0),
                        type=b.get("type", "text"),
                    )
                    for i, b in enumerate(data.get("blocks", []))
                ]

                return OcrPageResponse(
                    file_id=file_id,
                    bidder_id=bidder_id,
                    page_number=page_number,
                    doc_type=doc_type,
                    method=data.get("method", "unknown"),
                    doc_confidence=data.get("doc_confidence", 0.0),
                    routed_to_ocr=True,
                    blocks=blocks,
                )

            except httpx.HTTPStatusError as e:
                raise RuntimeError(
                    f"OCR service returned {e.response.status_code}: {e.response.text}"
                )
            except httpx.ConnectError:
                raise RuntimeError(
                    f"Cannot connect to OCR service at {self.base_url}. "
                    "Is the ocr container running?"
                )

    async def extract_batch(
        self,
        pages: List[Dict[str, Any]],
    ) -> List[OcrPageResponse]:
        """
        Process multiple pages. Each dict should have:
            image_bytes, doc_type, bidder_id, page_number, file_id
        """
        import asyncio

        tasks = [
            self.extract(
                image_bytes=p["image_bytes"],
                doc_type=p["doc_type"],
                bidder_id=p["bidder_id"],
                page_number=p["page_number"],
                file_id=p["file_id"],
            )
            for p in pages
        ]
        return await asyncio.gather(*tasks, return_exceptions=True)


ocr_client = OcrClient()

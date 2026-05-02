"""
TenderLens — F-03 Typed PDF Parser
Uses pdfplumber + PyMuPDF for native-text PDFs.
OCR is only called if text density < 0.85 (garbled text layer).
"""

import io
from typing import List, Dict, Any, Tuple

import pdfplumber
import fitz  # PyMuPDF

from app.shared.schemas import OcrBlockSchema


class TypedPdfParser:
    """
    Extracts text from digitally-created PDFs with embedded text layers.
    Falls back to OCR if text density is below 0.85 (garbled/image-heavy).
    """

    TEXT_DENSITY_THRESHOLD = 0.85

    def parse(self, pdf_bytes: bytes) -> Tuple[List[Dict[str, Any]], bool]:
        """
        Parse a typed PDF.

        Returns:
            (pages_data, needs_ocr)
            pages_data: list of dicts with page_number, blocks, confidence
            needs_ocr: True if text density is too low and OCR should be called
        """
        pages_data = []
        total_pages = 0
        pages_with_text = 0

        try:
            # Use pdfplumber for structured text extraction
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                total_pages = len(pdf.pages)

                for page_num, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    words = page.extract_words() or []

                    if len(text.strip()) > 20:
                        pages_with_text += 1

                    blocks = []
                    for i, word_group in enumerate(self._group_words_to_lines(words)):
                        blocks.append({
                            "block_id": f"blk_{page_num:03d}_{i:04d}",
                            "text": word_group["text"],
                            "bbox": word_group["bbox"],
                            "confidence": 0.95,  # Native text — high confidence
                            "type": "text",
                            "page_number": page_num,
                        })

                    # Extract tables separately
                    tables = page.extract_tables() or []
                    for ti, table in enumerate(tables):
                        for ri, row in enumerate(table):
                            for ci, cell in enumerate(row):
                                if cell and cell.strip():
                                    blocks.append({
                                        "block_id": f"blk_{page_num:03d}_tbl{ti}_{ri}_{ci}",
                                        "text": cell.strip(),
                                        "bbox": None,
                                        "confidence": 0.90,
                                        "type": "table_cell",
                                        "page_number": page_num,
                                    })

                    pages_data.append({
                        "page_number": page_num,
                        "blocks": blocks,
                        "text_length": len(text),
                    })

        except Exception as e:
            return [], True  # Fall back to OCR on any parsing error

        # Check text density
        text_density = pages_with_text / max(total_pages, 1)
        needs_ocr = text_density < self.TEXT_DENSITY_THRESHOLD

        return pages_data, needs_ocr

    @staticmethod
    def _group_words_to_lines(words: List[Dict]) -> List[Dict[str, Any]]:
        """Group individual words into line-level blocks."""
        if not words:
            return []

        lines = []
        current_line_words = [words[0]]

        for word in words[1:]:
            prev = current_line_words[-1]
            # Same line if y-coordinates are close
            if abs(word.get("top", 0) - prev.get("top", 0)) < 5:
                current_line_words.append(word)
            else:
                # Flush current line
                line_text = " ".join(w.get("text", "") for w in current_line_words)
                bbox = [
                    int(current_line_words[0].get("x0", 0)),
                    int(current_line_words[0].get("top", 0)),
                    int(current_line_words[-1].get("x1", 0)),
                    int(current_line_words[-1].get("bottom", 0)),
                ]
                lines.append({"text": line_text, "bbox": bbox})
                current_line_words = [word]

        # Final line
        if current_line_words:
            line_text = " ".join(w.get("text", "") for w in current_line_words)
            bbox = [
                int(current_line_words[0].get("x0", 0)),
                int(current_line_words[0].get("top", 0)),
                int(current_line_words[-1].get("x1", 0)),
                int(current_line_words[-1].get("bottom", 0)),
            ]
            lines.append({"text": line_text, "bbox": bbox})

        return lines


class ScannedPdfParser:
    """
    Handles scanned PDFs — converts each page to image, sends to OCR.
    Always calls the OCR service.
    """

    def extract_page_images(self, pdf_bytes: bytes) -> List[Dict[str, Any]]:
        """
        Convert each page of a scanned PDF to a PNG image.
        Returns list of {page_number, image_bytes}.
        """
        pages = []
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        for page_num in range(doc.page_count):
            page = doc[page_num]
            # Render at 300 DPI for OCR quality
            mat = fitz.Matrix(300 / 72, 300 / 72)
            pix = page.get_pixmap(matrix=mat)
            image_bytes = pix.tobytes("png")

            pages.append({
                "page_number": page_num,
                "image_bytes": image_bytes,
            })

        doc.close()
        return pages


class PhotoParser:
    """
    Handles phone-camera photos (JPEG/PNG).
    Applies OpenCV preprocessing then sends to OCR.
    """

    def prepare(self, image_bytes: bytes) -> bytes:
        """
        Apply OpenCV preprocessing to a photo before OCR.
        Delegates to the preprocess module.
        """
        from app.features.bidder_parsing.preprocess import ImagePreprocessor
        preprocessor = ImagePreprocessor()
        return preprocessor.full_pipeline(image_bytes)


class DocxParser:
    """
    Handles Word (.docx) files — uses python-docx.
    Never calls the OCR service.
    Flags documents with tracked changes.
    """

    def parse(self, docx_bytes: bytes) -> List[Dict[str, Any]]:
        """
        Extract text from a Word document.
        Returns blocks with high confidence (native text).
        """
        import docx as python_docx

        doc = python_docx.Document(io.BytesIO(docx_bytes))
        blocks = []
        has_tracked_changes = False

        for i, paragraph in enumerate(doc.paragraphs):
            text = paragraph.text.strip()
            if not text:
                continue

            # Check for tracked changes (revision marks)
            if paragraph._element.xml.find("w:del") != -1 or \
               paragraph._element.xml.find("w:ins") != -1:
                has_tracked_changes = True

            block_type = "text"
            if paragraph.style and paragraph.style.name.startswith("Heading"):
                block_type = "header"

            blocks.append({
                "block_id": f"blk_docx_{i:04d}",
                "text": text,
                "bbox": None,
                "confidence": 0.95 if not has_tracked_changes else 0.70,
                "type": block_type,
                "page_number": 0,  # docx doesn't have page numbers easily
            })

        # Extract tables
        for ti, table in enumerate(doc.tables):
            for ri, row in enumerate(table.rows):
                for ci, cell in enumerate(row.cells):
                    cell_text = cell.text.strip()
                    if cell_text:
                        blocks.append({
                            "block_id": f"blk_docx_tbl{ti}_{ri}_{ci}",
                            "text": cell_text,
                            "bbox": None,
                            "confidence": 0.90,
                            "type": "table_cell",
                            "page_number": 0,
                        })

        return blocks

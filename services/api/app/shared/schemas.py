"""
TenderLens — Pydantic Schemas (Shared)
These schemas are used across all features for validation and API responses.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime


# ══════════════════════════════════════════════════════════
# THRESHOLD SCHEMA
# ══════════════════════════════════════════════════════════
class ThresholdSchema(BaseModel):
    value: Any = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    boolean_expected: Optional[bool] = None
    unit: Optional[str] = None
    period: Optional[str] = None
    operator: str = "gte"  # gte | lte | eq | between | eq_string | semantic_match | boolean_match | modifier
    each_value: Optional[float] = None
    each_unit: Optional[str] = None
    effect: Optional[str] = None
    both_values: Optional[List[Any]] = None


# ══════════════════════════════════════════════════════════
# CRITERION SCHEMAS
# ══════════════════════════════════════════════════════════
class CriterionBase(BaseModel):
    criterion_id: str
    text: str
    type: str  # financial | technical | compliance | conditional
    mandatory: bool = True
    threshold: Optional[ThresholdSchema] = None
    source_section: Optional[str] = None
    source_page: Optional[int] = None
    weight: float = 0.0
    ambiguous: bool = False
    ambiguity_note: Optional[str] = None


class CriterionCreate(CriterionBase):
    pass


class CriterionUpdate(BaseModel):
    text: Optional[str] = None
    type: Optional[str] = None
    mandatory: Optional[bool] = None
    threshold: Optional[ThresholdSchema] = None
    weight: Optional[float] = None


class CriterionResponse(CriterionBase):
    id: str
    tender_id: str
    status: str
    prompt_version: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════════════════
# TENDER SCHEMAS
# ══════════════════════════════════════════════════════════
class TenderCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=512)
    description: Optional[str] = None


class TenderResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    lock_hash: Optional[str] = None
    prompt_version: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    criteria: List[CriterionResponse] = []

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════════════════
# CRITERION REGISTRY (Gemini extraction output)
# ══════════════════════════════════════════════════════════
class CriterionRegistryResponse(BaseModel):
    tender_id: str
    extracted_at: datetime
    prompt_version: str
    lock_hash: Optional[str] = None
    status: str
    criteria: List[CriterionBase]


# ══════════════════════════════════════════════════════════
# OCR BLOCK SCHEMA
# ══════════════════════════════════════════════════════════
class OcrBlockSchema(BaseModel):
    block_id: str
    text: str
    bbox: Optional[List[int]] = None  # [x1, y1, x2, y2]
    confidence: float
    type: str = "text"  # text | table_cell | header


class OcrPageResponse(BaseModel):
    file_id: str
    bidder_id: str
    page_number: int
    doc_type: str
    method: str
    doc_confidence: float
    routed_to_ocr: bool
    blocks: List[OcrBlockSchema]


# ══════════════════════════════════════════════════════════
# SCORING SCHEMAS
# ══════════════════════════════════════════════════════════
class CriterionScoreSchema(BaseModel):
    criterion_id: str
    extracted_value: Optional[str] = None
    source_block: Optional[str] = None
    source_page: Optional[int] = None
    normalised_score: float
    weighted_score: float
    verdict: str  # pass | fail | partial
    confidence: float
    layer: str  # deterministic | semantic | computation
    auto_approved: bool


class BidderScoreResponse(BaseModel):
    bidder_id: str
    bidder_name: str
    tender_id: str
    rank: Optional[int] = None
    final_score: float
    eligible: bool
    disqualified: bool
    disqualify_reason: Optional[str] = None
    criterion_scores: List[CriterionScoreSchema] = []
    rationale: Optional[str] = None
    computed_at: datetime

    class Config:
        from_attributes = True


class RankedOutputResponse(BaseModel):
    tender_id: str
    total_bidders: int
    eligible_count: int
    disqualified_count: int
    pending_reviews: int
    rankings: List[BidderScoreResponse]
    disqualified: List[BidderScoreResponse]


# ══════════════════════════════════════════════════════════
# FILE INGEST SCHEMAS
# ══════════════════════════════════════════════════════════
class FileManifestItem(BaseModel):
    file_id: str
    original_filename: str
    sha256: str
    mime_type: str
    format_detected: str
    minio_path: str


class IngestResponse(BaseModel):
    bidder_id: str
    tender_id: str
    files: List[FileManifestItem]
    message: str


# ══════════════════════════════════════════════════════════
# REVIEWER SCHEMAS
# ══════════════════════════════════════════════════════════
class ReviewerQueueItemResponse(BaseModel):
    id: str
    tender_name: Optional[str] = None
    bidder_name: Optional[str] = None
    criterion_text: Optional[str] = None
    flag_reason: Optional[str] = None
    extracted_value: Optional[str] = None
    ai_verdict: Optional[str] = None
    confidence: Optional[float] = None
    status: str
    priority: int

    class Config:
        from_attributes = True


class ReviewerDecision(BaseModel):
    action: str  # approve | reject | override | escalate
    corrected_value: Optional[str] = None
    reason: str = Field(..., min_length=1)  # NOT NULL enforced


# ══════════════════════════════════════════════════════════
# AUDIT SCHEMAS
# ══════════════════════════════════════════════════════════
class AuditLogEntry(BaseModel):
    id: str
    event_type: str
    payload: dict
    prev_hash: Optional[str] = None
    this_hash: str
    ts: datetime

    class Config:
        from_attributes = True

"""
TenderLens — Core Database Models
All 12 tables from PRD Section 8.
"""

import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime,
    ForeignKey, JSON, Enum as SAEnum, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.shared.database import Base


# ── Helper ──
def generate_uuid():
    return str(uuid.uuid4())


# ══════════════════════════════════════════════════════════
# 1. TENDERS
# ══════════════════════════════════════════════════════════
class Tender(Base):
    __tablename__ = "tenders"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    lock_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    prompt_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="draft"
    )  # draft → analysed → locked → evaluated → closed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    criteria = relationship("Criterion", back_populates="tender", cascade="all, delete-orphan")
    bidders = relationship("Bidder", back_populates="tender", cascade="all, delete-orphan")
    bidder_scores = relationship("BidderScore", back_populates="tender", cascade="all, delete-orphan")


# ══════════════════════════════════════════════════════════
# 2. CRITERIA (Extracted from Tender PDF by Gemini)
# ══════════════════════════════════════════════════════════
class Criterion(Base):
    __tablename__ = "criteria"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    tender_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenders.id"), nullable=False)
    criterion_id: Mapped[str] = mapped_column(String(32), nullable=False)  # C1, C2, ...
    text: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # financial | technical | compliance | conditional
    mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    threshold_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    source_section: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    source_page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ambiguous: Mapped[bool] = mapped_column(Boolean, default=False)
    ambiguity_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft")  # draft | locked
    prompt_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    tender = relationship("Tender", back_populates="criteria")
    verdicts = relationship("Verdict", back_populates="criterion", cascade="all, delete-orphan")
    extractions = relationship("Extraction", back_populates="criterion", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("tender_id", "criterion_id", name="uq_tender_criterion"),
    )


# ══════════════════════════════════════════════════════════
# 3. BIDDERS
# ══════════════════════════════════════════════════════════
class Bidder(Base):
    __tablename__ = "bidders"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    tender_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenders.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    pseudonym_id: Mapped[str] = mapped_column(String(64), nullable=False)  # Used in Gemini calls
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending | parsing | parsed | scored
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    tender = relationship("Tender", back_populates="bidders")
    files = relationship("IngestFile", back_populates="bidder", cascade="all, delete-orphan")
    scores = relationship("BidderScore", back_populates="bidder", cascade="all, delete-orphan")
    verdicts = relationship("Verdict", back_populates="bidder", cascade="all, delete-orphan")


# ══════════════════════════════════════════════════════════
# 4. INGEST FILES
# ══════════════════════════════════════════════════════════
class IngestFile(Base):
    __tablename__ = "ingest_files"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    bidder_id: Mapped[str] = mapped_column(String(64), ForeignKey("bidders.id"), nullable=False)
    minio_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    sha256: Mapped[str] = mapped_column(String(128), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    format_detected: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # typed_pdf | scanned | photo | docx
    original_filename: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    bidder = relationship("Bidder", back_populates="files")
    ocr_blocks = relationship("OcrBlock", back_populates="file", cascade="all, delete-orphan")
    extractions = relationship("Extraction", back_populates="file", cascade="all, delete-orphan")


# ══════════════════════════════════════════════════════════
# 5. OCR BLOCKS (Direct output of local OCR service)
# ══════════════════════════════════════════════════════════
class OcrBlock(Base):
    __tablename__ = "ocr_blocks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    file_id: Mapped[str] = mapped_column(String(64), ForeignKey("ingest_files.id"), nullable=False)
    block_id: Mapped[str] = mapped_column(String(64), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    bbox: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)  # [x1, y1, x2, y2]
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    type: Mapped[str] = mapped_column(String(32), default="text")  # text | table_cell | header
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    file = relationship("IngestFile", back_populates="ocr_blocks")


# ══════════════════════════════════════════════════════════
# 6. EXTRACTIONS (one row per file × criterion pair)
# ══════════════════════════════════════════════════════════
class Extraction(Base):
    __tablename__ = "extractions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    file_id: Mapped[str] = mapped_column(String(64), ForeignKey("ingest_files.id"), nullable=False)
    criterion_id: Mapped[str] = mapped_column(String(64), ForeignKey("criteria.id"), nullable=False)
    value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_block_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    method: Mapped[str] = mapped_column(String(64), nullable=False)  # deterministic | semantic | computation
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    file = relationship("IngestFile", back_populates="extractions")
    criterion = relationship("Criterion", back_populates="extractions")


# ══════════════════════════════════════════════════════════
# 7. BIDDER SCORES
# ══════════════════════════════════════════════════════════
class BidderScore(Base):
    __tablename__ = "bidder_scores"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    bidder_id: Mapped[str] = mapped_column(String(64), ForeignKey("bidders.id"), nullable=False)
    tender_id: Mapped[str] = mapped_column(String(64), ForeignKey("tenders.id"), nullable=False)
    rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    final_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    eligible: Mapped[bool] = mapped_column(Boolean, default=True)
    disqualified: Mapped[bool] = mapped_column(Boolean, default=False)
    disqualify_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    criterion_scores_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Gemini plain-English string
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    bidder = relationship("Bidder", back_populates="scores")
    tender = relationship("Tender", back_populates="bidder_scores")


# ══════════════════════════════════════════════════════════
# 8. VERDICTS (per-criterion per-bidder)
# ══════════════════════════════════════════════════════════
class Verdict(Base):
    __tablename__ = "verdicts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    criterion_id: Mapped[str] = mapped_column(String(64), ForeignKey("criteria.id"), nullable=False)
    bidder_id: Mapped[str] = mapped_column(String(64), ForeignKey("bidders.id"), nullable=False)
    verdict: Mapped[str] = mapped_column(String(32), nullable=False)  # pass | fail | partial
    normalised_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    weighted_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    layer: Mapped[str] = mapped_column(String(32), nullable=False)  # deterministic | semantic | computation
    auto_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    criterion = relationship("Criterion", back_populates="verdicts")
    bidder = relationship("Bidder", back_populates="verdicts")
    reviewer_queue_items = relationship("ReviewerQueueItem", back_populates="verdict", cascade="all, delete-orphan")


# ══════════════════════════════════════════════════════════
# 9. REVIEWER QUEUE
# ══════════════════════════════════════════════════════════
class ReviewerQueueItem(Base):
    __tablename__ = "reviewer_queue"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    verdict_id: Mapped[str] = mapped_column(String(64), ForeignKey("verdicts.id"), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="pending"
    )  # pending | in_progress | decided | escalated
    flag_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assigned_to: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    verdict = relationship("Verdict", back_populates="reviewer_queue_items")
    actions = relationship("ReviewerAction", back_populates="queue_item", cascade="all, delete-orphan")


# ══════════════════════════════════════════════════════════
# 10. REVIEWER ACTIONS (append-only)
# ══════════════════════════════════════════════════════════
class ReviewerAction(Base):
    __tablename__ = "reviewer_actions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    queue_item_id: Mapped[str] = mapped_column(String(64), ForeignKey("reviewer_queue.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)  # approve | reject | override | escalate
    corrected_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)  # NOT NULL enforced at DB level
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    is_training_candidate: Mapped[bool] = mapped_column(Boolean, default=False)
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    queue_item = relationship("ReviewerQueueItem", back_populates="actions")


# ══════════════════════════════════════════════════════════
# 11. AUDIT LOG (append-only, hash chain)
# ══════════════════════════════════════════════════════════
class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=generate_uuid)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    prev_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    this_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

"""
TenderLens API — FastAPI Application Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

app = FastAPI(
    title=settings.app_name,
    description="AI-Powered Tender Evaluation & Eligibility Analysis",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health Check ──
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "tenderlens-api"}


# ── Feature Routers ──
# Each feature registers its own router — one line per feature
from app.features.ingest.router import router as ingest_router
from app.features.tender_analysis.router import router as tender_analysis_router
from app.features.bidder_parsing.router import router as bidder_parsing_router
from app.features.matching.router import router as matching_router
from app.features.scoring.router import router as scoring_router
from app.features.reviewer.router import router as reviewer_router
from app.features.audit.router import router as audit_router
from app.features.feedback.router import router as feedback_router

app.include_router(ingest_router, prefix="/api/v1/ingest", tags=["Ingest"])
app.include_router(tender_analysis_router, prefix="/api/v1/tender", tags=["Tender Analysis"])
app.include_router(bidder_parsing_router, prefix="/api/v1/bidder", tags=["Bidder Parsing"])
app.include_router(matching_router, prefix="/api/v1/matching", tags=["Matching"])
app.include_router(scoring_router, prefix="/api/v1/tender", tags=["Scoring"])
app.include_router(reviewer_router, prefix="/api/v1/reviewer", tags=["Reviewer"])
app.include_router(audit_router, prefix="/api/v1/audit", tags=["Audit"])
app.include_router(feedback_router, prefix="/api/v1/feedback", tags=["Feedback"])

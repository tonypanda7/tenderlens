"""
TenderLens API — Application Configuration
Loads all settings from environment variables with sensible defaults.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Central configuration — loaded from .env file."""

    # ── App ──
    app_name: str = "TenderLens API"
    api_debug: bool = True
    secret_key: str = "dev-secret-key-change-in-production"

    # ── Gemini 2.5 Flash ──
    gemini_api_key: str = ""
    gemini_max_retries: int = 4
    max_tokens_per_tender: int = 900_000
    daily_spend_cap: float = 10.00

    # ── OCR Service (Local) ──
    ocr_service_url: str = "http://ocr-service:8001"
    ocr_api_key: str = ""

    # ── PostgreSQL ──
    postgres_user: str = "tenderlens"
    postgres_password: str = "tenderlens_dev_2026"
    postgres_db: str = "tenderlens"
    postgres_host: str = "db"
    postgres_port: int = 5432

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # ── MinIO ──
    minio_root_user: str = "tenderlens"
    minio_root_password: str = "minio_dev_2026"
    minio_endpoint: str = "storage:9000"
    minio_bucket: str = "tenderlens-docs"
    minio_use_ssl: bool = False

    # ── Redis / Celery ──
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"

    # ── Confidence Thresholds ──
    auto_approve_confidence: float = 0.85
    reviewer_queue_confidence: float = 0.60
    flag_with_image_confidence: float = 0.60

    # ── Default Scoring Weights (%) ──
    default_financial_weight: int = 35
    default_technical_weight: int = 35
    default_compliance_weight: int = 20
    default_optional_weight: int = 10

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

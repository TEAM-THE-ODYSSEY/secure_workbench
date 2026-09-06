"""
Configuration management for MRPL Air-Gapped Knowledge Platform using Pydantic Settings.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class RAGConfig(BaseSettings):
    """Global configuration settings for MRPL Knowledge Platform."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Database Settings ---
    POSTGRES_URI: str = "postgresql+psycopg://postgres:postgres@localhost:5432/mrpl_rag"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    USE_IN_MEMORY_FALLBACK: bool = False

    # --- Redis / Celery ---
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # --- MinIO Object Storage ---
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_SECURE: bool = False
    MINIO_BUCKET_RAW: str = "raw"
    MINIO_BUCKET_TRUSTED: str = "trusted"
    MINIO_BUCKET_QUARANTINE: str = "quarantine"
    MINIO_ENABLED: bool = True  # False falls back to LocalObjectStorage

    # --- Embedding Settings ---
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-m3"
    EMBEDDING_DIMENSION: int = 1024
    EMBEDDING_DEVICE: str = "cpu"  # cpu or cuda
    EMBEDDING_BATCH_SIZE: int = 32
    EMBEDDING_FALLBACK_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_FALLBACK_DIMENSION: int = 384

    # --- Chunking Settings ---
    DEFAULT_CHUNK_SIZE: int = 512
    DEFAULT_CHUNK_OVERLAP: int = 64
    SEMANTIC_SIMILARITY_THRESHOLD: float = 0.75

    # --- Retrieval Settings ---
    DEFAULT_TOP_K: int = 5
    HYBRID_ALPHA: float = 0.5  # Weight for vector vs keyword (0.0 to 1.0)
    RERANKER_MODEL_NAME: Optional[str] = "BAAI/bge-reranker-v2-m3"
    RERANKER_FALLBACK_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    RERANK_TOP_N: int = 10

    # --- Storage Settings ---
    OBJECT_STORAGE_DIR: str = "./data/object_storage"

    # --- Security Settings ---
    SECURITY_ENABLED: bool = True
    CLAMAV_HOST: str = "localhost"
    CLAMAV_PORT: int = 3310
    CLAMAV_ENABLED: bool = False  # Disabled by default for dev
    PROMPT_INJECTION_ENABLED: bool = True
    CONTRADICTION_DETECTION_ENABLED: bool = True
    PROMPT_INJECTION_ML_ENABLED: bool = False  # ML classifier off by default

    # --- NLP Settings ---
    SPACY_MODEL: str = "en_core_web_sm"
    SPACY_ENABLED: bool = True

    # --- Ingestion Settings ---
    WATCHER_POLL_INTERVAL: int = 5
    MAX_FILE_SIZE_MB: int = 100
    ALLOWED_EXTENSIONS: str = ".pdf,.docx,.xlsx,.xls,.txt,.csv"

    # --- Reasoning Agent vLLM Settings ---
    VLLM_API_BASE: str = "http://host.docker.internal:8080/v1"
    PRIMARY_MODEL_NAME: str = "Qwen3-4B"
    FALLBACK_MODEL_NAME: str = "Qwen3-1.7B"

    # --- Logging ---
    LOG_LEVEL: str = "INFO"


# Instantiate global config singleton
config = RAGConfig()

"""
Configuration management for MRPL RAG architecture using Pydantic Settings.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class RAGConfig(BaseSettings):
    """Global configuration settings for MRPL RAG System."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database Settings
    POSTGRES_URI: str = "postgresql+psycopg://postgres:postgres@localhost:5432/mrpl_rag"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    USE_IN_MEMORY_FALLBACK: bool = True  # Allows pipeline execution without PostgreSQL running

    # Embedding Settings
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384
    EMBEDDING_DEVICE: str = "cpu"  # cpu or cuda
    EMBEDDING_BATCH_SIZE: int = 32

    # Chunking Settings
    DEFAULT_CHUNK_SIZE: int = 512
    DEFAULT_CHUNK_OVERLAP: int = 64
    SEMANTIC_SIMILARITY_THRESHOLD: float = 0.75

    # Retrieval Settings
    DEFAULT_TOP_K: int = 5
    HYBRID_ALPHA: float = 0.5  # Weight for vector vs keyword (0.0 to 1.0)
    RERANKER_MODEL_NAME: Optional[str] = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    RERANK_TOP_N: int = 10

    # Storage Settings
    OBJECT_STORAGE_DIR: str = "./data/object_storage"

    # Ingestion & Queue Settings
    WATCHER_POLL_INTERVAL: int = 5
    MAX_FILE_SIZE_MB: int = 100

    # Logging
    LOG_LEVEL: str = "INFO"


# Instantiate global config singleton
config = RAGConfig()

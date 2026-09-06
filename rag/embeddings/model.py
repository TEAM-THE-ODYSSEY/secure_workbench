"""
Configuration and loader metadata for embedding models.
"""

import logging
from typing import Optional
from pydantic import BaseModel
from rag.config import config

logger = logging.getLogger(__name__)


class EmbeddingModelConfig(BaseModel):
    """Configuration encapsulation for embedding model instantiation."""
    model_name: str = config.EMBEDDING_MODEL_NAME
    dimension: int = config.EMBEDDING_DIMENSION
    device: str = config.EMBEDDING_DEVICE
    batch_size: int = config.EMBEDDING_BATCH_SIZE
    normalize_embeddings: bool = True

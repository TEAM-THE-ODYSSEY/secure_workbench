"""
Embedder implementation wrapping SentenceTransformers for generating vector representations.
"""

from abc import ABC, abstractmethod
import logging
from typing import List, Optional
import numpy as np

from rag.embeddings.model import EmbeddingModelConfig

logger = logging.getLogger(__name__)


class BaseEmbedder(ABC):
    """Abstract interface for text embedding engines."""

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Embed a single text string into a vector."""
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of text strings into vector representations."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the vector dimensionality."""
        pass


class SentenceTransformerEmbedder(BaseEmbedder):
    """Embedder using SentenceTransformers library."""

    def __init__(self, model_config: Optional[EmbeddingModelConfig] = None):
        self.config = model_config or EmbeddingModelConfig()
        self._model = None

    def _get_model(self):
        """Lazy load SentenceTransformer model."""
        if self._model is None:
            logger.info(f"Loading SentenceTransformer model '{self.config.model_name}' on {self.config.device}...")
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.config.model_name, device=self.config.device)
            except Exception as e:
                logger.error(f"Failed to load SentenceTransformer model {self.config.model_name}: {e}", exc_info=True)
                raise e
        return self._model

    def embed_text(self, text: str) -> List[float]:
        """Embed single text string."""
        if not text.strip():
            return [0.0] * self.config.dimension
        
        batch_results = self.embed_batch([text])
        return batch_results[0]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed batch of text strings."""
        if not texts:
            return []

        cleaned_texts = [t if t.strip() else "empty" for t in texts]

        try:
            model = self._get_model()
            embeddings = model.encode(
                cleaned_texts,
                batch_size=self.config.batch_size,
                show_progress_bar=False,
                normalize_embeddings=self.config.normalize_embeddings,
            )
            return [emb.tolist() for emb in embeddings]
        except Exception as e:
            logger.error(f"Error during batch embedding generation: {e}", exc_info=True)
            # Fallback zero vectors on failure
            return [[0.0] * self.config.dimension for _ in texts]

    @property
    def dimension(self) -> int:
        return self.config.dimension


class Embedder(SentenceTransformerEmbedder):
    """Default Embedder alias."""
    pass

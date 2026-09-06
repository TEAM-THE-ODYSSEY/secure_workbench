"""
pgvector storage abstraction for vector indexing, cosine similarity, and metadata filtering.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from rag.chunking.semantic_chunker import Chunk

logger = logging.getLogger(__name__)


def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Calculate cosine similarity between two numeric vectors."""
    a = np.array(vec_a, dtype=float)
    b = np.array(vec_b, dtype=float)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


class PgVectorStore:
    """Abstraction for pgvector operations and vector similarity queries."""

    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        # In-memory vector cache for fast vector operations when running fallback or local search
        self._vector_store: Dict[str, Tuple[Chunk, List[float]]] = {}

    def insert_chunk_vector(self, chunk: Chunk, vector: List[float]) -> None:
        """Store chunk and vector representation."""
        chunk.embedding = vector
        self._vector_store[chunk.chunk_id] = (chunk, vector)

    def search_similar(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[Chunk, float]]:
        """Perform similarity search matching vector and metadata filters."""
        results: List[Tuple[Chunk, float]] = []

        for chunk_id, (chunk, vector) in self._vector_store.items():
            # Check metadata filters
            if filters:
                match = True
                chunk_meta = chunk.metadata or {}
                for key, val in filters.items():
                    if val is not None:
                        # Normalize string values for comparison
                        chunk_val = chunk_meta.get(key)
                        if isinstance(val, str) and isinstance(chunk_val, str):
                            if val.lower() != chunk_val.lower():
                                match = False
                                break
                        elif chunk_val != val:
                            match = False
                            break
                if not match:
                    continue

            score = cosine_similarity(query_vector, vector)
            results.append((chunk, score))

        # Sort descending by similarity score
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def clear(self) -> None:
        """Clear cached vectors."""
        self._vector_store.clear()

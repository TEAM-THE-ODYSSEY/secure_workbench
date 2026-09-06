"""
Deduplicator for filtering out exact or near-duplicate passages from retrieved chunk results.
"""

import logging
from typing import List, Tuple
from rag.chunking.semantic_chunker import Chunk

logger = logging.getLogger(__name__)


class ContextDeduplicator:
    """Removes redundant/duplicate chunks based on text similarity thresholding."""

    def __init__(self, jaccard_threshold: float = 0.85):
        self.jaccard_threshold = jaccard_threshold

    def _jaccard_similarity(self, text_a: str, text_b: str) -> float:
        set_a = set(text_a.lower().split())
        set_b = set(text_b.lower().split())
        if not set_a or not set_b:
            return 0.0
        intersection = set_a.intersection(set_b)
        union = set_a.union(set_b)
        return len(intersection) / len(union)

    def deduplicate(self, scored_chunks: List[Tuple[Chunk, float]]) -> List[Tuple[Chunk, float]]:
        """Filter out near-duplicate chunks while preserving highest-scoring instances."""
        unique_results: List[Tuple[Chunk, float]] = []

        for chunk, score in scored_chunks:
            is_duplicate = False
            for kept_chunk, _ in unique_results:
                sim = self._jaccard_similarity(chunk.content, kept_chunk.content)
                if sim >= self.jaccard_threshold:
                    logger.debug(f"Filtering near-duplicate chunk {chunk.chunk_id} (Similarity: {sim:.2f})")
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_results.append((chunk, score))

        logger.info(f"ContextDeduplicator reduced {len(scored_chunks)} chunk(s) to {len(unique_results)} unique chunk(s).")
        return unique_results

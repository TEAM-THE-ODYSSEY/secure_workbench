"""
Hybrid search module combining vector similarity search and BM25 keyword search
using Reciprocal Rank Fusion (RRF) or weighted score fusion.
"""

import logging
from typing import Dict, List, Optional, Tuple

from rag.chunking.semantic_chunker import Chunk
from rag.config import config
from rag.retrieval.vector_search import VectorSearch
from rag.retrieval.keyword_search import KeywordSearch
from rag.retrieval.metadata_filter import FilterCondition

logger = logging.getLogger(__name__)


class HybridSearch:
    """Combines vector search and keyword search using Reciprocal Rank Fusion (RRF)."""

    def __init__(
        self,
        vector_search: VectorSearch,
        keyword_search: KeywordSearch,
        alpha: float = config.HYBRID_ALPHA,  # Weight factor: 0.0 -> 100% keyword, 1.0 -> 100% vector
        rrf_k: int = 60,
    ):
        self.vector_search = vector_search
        self.keyword_search = keyword_search
        self.alpha = alpha
        self.rrf_k = rrf_k

    def search(
        self,
        query_text: str,
        top_k: int = 10,
        filter_condition: Optional[FilterCondition] = None,
    ) -> List[Tuple[Chunk, float]]:
        """Perform hybrid retrieval using RRF fusion strategy."""
        fetch_k = top_k * 2

        # 1. Fetch vector search results
        vector_results = self.vector_search.search(
            query_text=query_text,
            top_k=fetch_k,
            filter_condition=filter_condition,
        )

        # 2. Fetch keyword search results
        keyword_results = self.keyword_search.search(
            query_text=query_text,
            top_k=fetch_k,
            filter_condition=filter_condition,
        )

        # 3. Apply Reciprocal Rank Fusion (RRF)
        rrf_scores: Dict[str, float] = {}
        chunk_map: Dict[str, Chunk] = {}

        # Process vector ranks
        for rank, (chunk, v_score) in enumerate(vector_results, start=1):
            chunk_map[chunk.chunk_id] = chunk
            vector_rrf = 1.0 / (self.rrf_k + rank)
            rrf_scores[chunk.chunk_id] = rrf_scores.get(chunk.chunk_id, 0.0) + (self.alpha * vector_rrf)

        # Process keyword ranks
        for rank, (chunk, k_score) in enumerate(keyword_results, start=1):
            chunk_map[chunk.chunk_id] = chunk
            keyword_rrf = 1.0 / (self.rrf_k + rank)
            rrf_scores[chunk.chunk_id] = rrf_scores.get(chunk.chunk_id, 0.0) + ((1.0 - self.alpha) * keyword_rrf)

        # Build fused result list
        fused: List[Tuple[Chunk, float]] = [
            (chunk_map[cid], score) for cid, score in rrf_scores.items()
        ]
        fused.sort(key=lambda x: x[1], reverse=True)

        logger.info(
            f"HybridSearch fused {len(vector_results)} vector & {len(keyword_results)} keyword results into {len(fused[:top_k])} top chunks."
        )
        return fused[:top_k]

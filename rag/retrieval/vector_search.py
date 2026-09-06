"""
Vector similarity search module using Embedder interface and PgVectorStore abstraction.
"""

import logging
from typing import Dict, List, Optional, Tuple

from rag.chunking.semantic_chunker import Chunk
from rag.embeddings.embedder import BaseEmbedder
from rag.storage.pgvector import PgVectorStore
from rag.retrieval.metadata_filter import FilterCondition

logger = logging.getLogger(__name__)


class VectorSearch:
    """Executes semantic similarity search against vector store."""

    def __init__(self, embedder: BaseEmbedder, vector_store: PgVectorStore):
        self.embedder = embedder
        self.vector_store = vector_store

    def search(
        self,
        query_text: str,
        top_k: int = 10,
        filter_condition: Optional[FilterCondition] = None,
    ) -> List[Tuple[Chunk, float]]:
        """Compute query vector and execute vector similarity search."""
        query_vector = self.embedder.embed_text(query_text)
        filters_dict = filter_condition.to_dict() if filter_condition else None

        results = self.vector_store.search_similar(
            query_vector=query_vector,
            top_k=top_k,
            filters=filters_dict,
        )

        logger.info(f"VectorSearch returned {len(results)} chunk result(s) for query: '{query_text[:40]}...'")
        return results

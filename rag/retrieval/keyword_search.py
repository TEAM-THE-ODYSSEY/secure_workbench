"""
BM25 Keyword search module for technical terms, equipment tag numbers, and exact code retrieval.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple
from rank_bm25 import BM25Okapi

from rag.chunking.semantic_chunker import Chunk
from rag.retrieval.metadata_filter import FilterCondition, MetadataFilter

logger = logging.getLogger(__name__)


class KeywordSearch:
    """Executes BM25 keyword search over registered document chunks."""

    def __init__(self):
        self._chunks: List[Chunk] = []
        self._corpus: List[List[str]] = []
        self._bm25: Optional[BM25Okapi] = None

    def _tokenize(self, text: str) -> List[str]:
        """Simple whitespace and punctuation tokenizer."""
        return [w.lower() for w in re.findall(r"\b[A-Za-z0-9\-]+\b", text)]

    def index_chunks(self, chunks: List[Chunk]) -> None:
        """Build or update BM25 index with chunks."""
        self._chunks = chunks
        self._corpus = [self._tokenize(c.content) for c in chunks]
        if self._corpus:
            self._bm25 = BM25Okapi(self._corpus)
            logger.info(f"KeywordSearch indexed {len(chunks)} chunks for BM25 search.")

    def search(
        self,
        query_text: str,
        top_k: int = 10,
        filter_condition: Optional[FilterCondition] = None,
    ) -> List[Tuple[Chunk, float]]:
        """Search chunks using BM25 keyword matching."""
        if not self._bm25 or not self._chunks:
            return []

        tokenized_query = self._tokenize(query_text)
        if not tokenized_query:
            return []

        scores = self._bm25.get_scores(tokenized_query)
        scored_chunks: List[Tuple[Chunk, float]] = []

        for idx, score in enumerate(scores):
            if score <= 0:
                continue

            chunk = self._chunks[idx]

            # Apply metadata filtering
            if filter_condition and not MetadataFilter.match(chunk.metadata or {}, filter_condition):
                continue

            scored_chunks.append((chunk, float(score)))

        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        logger.info(f"KeywordSearch returned {len(scored_chunks[:top_k])} result(s) for query: '{query_text[:40]}...'")
        return scored_chunks[:top_k]

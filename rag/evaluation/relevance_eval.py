"""
Relevance evaluation module for scoring context quality against user intent and ground truth answers.
"""

import logging
from typing import Optional
from pydantic import BaseModel

from rag.embeddings.embedder import BaseEmbedder
from rag.storage.pgvector import cosine_similarity

logger = logging.getLogger(__name__)


class RelevanceEvalResult(BaseModel):
    semantic_similarity: float
    keyword_coverage: float
    combined_relevance_score: float


class RelevanceEvaluator:
    """Evaluates context relevance using semantic embedding similarity and keyword coverage."""

    def __init__(self, embedder: Optional[BaseEmbedder] = None):
        self.embedder = embedder

    def evaluate_relevance(self, query: str, context_text: str, ground_truth: Optional[str] = None) -> RelevanceEvalResult:
        """Calculate relevance score between query/ground_truth and generated context text."""
        if not context_text.strip():
            return RelevanceEvalResult(semantic_similarity=0.0, keyword_coverage=0.0, combined_relevance_score=0.0)

        # Keyword coverage
        query_words = set(w.lower() for w in query.split() if len(w) > 2)
        context_lower = context_text.lower()
        matched = sum(1 for w in query_words if w in context_lower)
        coverage = matched / float(len(query_words)) if query_words else 1.0

        # Semantic similarity
        sim = 0.0
        if self.embedder:
            target_text = ground_truth if ground_truth else query
            vec_target = self.embedder.embed_text(target_text)
            vec_context = self.embedder.embed_text(context_text[:1000])  # Sample first 1k chars
            sim = cosine_similarity(vec_target, vec_context)

        combined = (sim * 0.6) + (coverage * 0.4) if self.embedder else coverage
        return RelevanceEvalResult(
            semantic_similarity=float(sim),
            keyword_coverage=float(coverage),
            combined_relevance_score=float(combined),
        )

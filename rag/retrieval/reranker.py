"""
Reranking abstractions and implementations for refining candidate retrieved chunks.
"""

from abc import ABC, abstractmethod
import logging
from typing import List, Optional, Tuple

from rag.chunking.semantic_chunker import Chunk
from rag.config import config

logger = logging.getLogger(__name__)


class Reranker(ABC):
    """Abstract interface for passage reranking engines."""

    @abstractmethod
    def rerank(self, query: str, candidate_chunks: List[Tuple[Chunk, float]], top_n: int = 5) -> List[Tuple[Chunk, float]]:
        """Rerank candidate chunks according to relevance to query."""
        pass


class ReciprocalReranker(Reranker):
    """Rule-based and term frequency density reranker requiring no external transformer weights."""

    def rerank(self, query: str, candidate_chunks: List[Tuple[Chunk, float]], top_n: int = 5) -> List[Tuple[Chunk, float]]:
        if not candidate_chunks:
            return []

        query_terms = set(w.lower() for w in query.split() if len(w) > 2)
        reranked: List[Tuple[Chunk, float]] = []

        for chunk, orig_score in candidate_chunks:
            content_lower = chunk.content.lower()
            matching_terms = sum(1 for term in query_terms if term in content_lower)
            term_density = matching_terms / max(len(query_terms), 1)

            # Boost exact section title matches or equipment tag matches
            title_boost = 0.2 if chunk.section_title and any(t in chunk.section_title.lower() for t in query_terms) else 0.0
            
            final_score = (orig_score * 0.6) + (term_density * 0.3) + title_boost
            reranked.append((chunk, float(final_score)))

        reranked.sort(key=lambda x: x[1], reverse=True)
        return reranked[:top_n]


class CrossEncoderReranker(Reranker):
    """Reranker using a Cross-Encoder transformer model."""

    def __init__(self, model_name: Optional[str] = config.RERANKER_MODEL_NAME):
        self.model_name = model_name
        self._model = None
        self._fallback_reranker = ReciprocalReranker()

    def _get_model(self):
        if self._model is None and self.model_name:
            try:
                from sentence_transformers import CrossEncoder
                logger.info(f"Loading CrossEncoder reranker model: {self.model_name}...")
                self._model = CrossEncoder(self.model_name)
            except Exception as e:
                logger.warning(f"Could not load CrossEncoder model {self.model_name} ({e}). Using ReciprocalReranker fallback.")
                self._model = False
        return self._model

    def rerank(self, query: str, candidate_chunks: List[Tuple[Chunk, float]], top_n: int = 5) -> List[Tuple[Chunk, float]]:
        if not candidate_chunks:
            return []

        model = self._get_model()
        if not model:
            return self._fallback_reranker.rerank(query, candidate_chunks, top_n=top_n)

        try:
            pairs = [[query, chunk.content] for chunk, _ in candidate_chunks]
            scores = model.predict(pairs)
            
            scored_list: List[Tuple[Chunk, float]] = []
            for (chunk, _), score in zip(candidate_chunks, scores):
                scored_list.append((chunk, float(score)))

            scored_list.sort(key=lambda x: x[1], reverse=True)
            logger.info(f"CrossEncoderReranker reranked {len(candidate_chunks)} candidate(s) down to top {top_n}")
            return scored_list[:top_n]
        except Exception as e:
            logger.error(f"CrossEncoder error: {e}. Falling back to ReciprocalReranker.")
            return self._fallback_reranker.rerank(query, candidate_chunks, top_n=top_n)


class BGEReranker(Reranker):
    """
    Reranker using BGE Reranker v2 (BAAI/bge-reranker-v2-m3) via FlagEmbedding or CrossEncoder.
    Provides production state-of-the-art multilingual and technical query-document relevance scoring.
    """

    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3"):
        self.model_name = model_name
        self._model = None
        self._is_flag_model = False
        self._fallback = ReciprocalReranker()

    def _get_model(self):
        if self._model is None:
            try:
                from FlagEmbedding import FlagReranker
                logger.info(f"Loading BGE Reranker via FlagEmbedding: {self.model_name}...")
                self._model = FlagReranker(self.model_name, use_fp16=False)
                self._is_flag_model = True
            except Exception as e:
                logger.warning(f"FlagReranker load failed ({e}), attempting CrossEncoder fallback...")
                try:
                    from sentence_transformers import CrossEncoder
                    self._model = CrossEncoder(self.model_name)
                    self._is_flag_model = False
                except Exception as ex:
                    logger.warning(f"Could not load BGE reranker model {self.model_name}: {ex}. Using ReciprocalReranker fallback.")
                    self._model = False
        return self._model

    def rerank(
        self,
        query: str,
        candidate_chunks: List[Tuple[Chunk, float]],
        top_n: int = 5,
    ) -> List[Tuple[Chunk, float]]:
        if not candidate_chunks:
            return []

        model = self._get_model()
        if not model:
            return self._fallback.rerank(query, candidate_chunks, top_n=top_n)

        try:
            pairs = [[query, chunk.content] for chunk, _ in candidate_chunks]
            if self._is_flag_model:
                scores = model.compute_score(pairs, normalize=True)
                if isinstance(scores, (float, int)):
                    scores = [scores]
            else:
                scores = model.predict(pairs)

            scored: List[Tuple[Chunk, float]] = []
            for (chunk, _), score in zip(candidate_chunks, scores):
                scored.append((chunk, float(score)))

            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[:top_n]
        except Exception as e:
            logger.error(f"BGEReranker error: {e}. Falling back to ReciprocalReranker.")
            return self._fallback.rerank(query, candidate_chunks, top_n=top_n)


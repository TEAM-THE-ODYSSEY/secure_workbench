"""
Retrieval evaluation metrics (Precision@K, Recall@K, MRR, Hit Rate).
"""

import logging
from typing import List
from pydantic import BaseModel

from rag.chunking.semantic_chunker import Chunk
from rag.evaluation.test_dataset import EvalTestCase, EvaluationDataset

logger = logging.getLogger(__name__)


class RetrievalEvalResult(BaseModel):
    total_queries: int
    precision_at_k: float
    recall_at_k: float
    mrr: float
    hit_rate: float
    k: int


class RetrievalEvaluator:
    """Evaluates accuracy of retrieval pipelines using standard IR metrics."""

    def evaluate_test_case(self, test_case: EvalTestCase, retrieved_chunks: List[Chunk], k: int = 5) -> dict:
        """Evaluate a single test case against top_k retrieved chunks."""
        top_k_chunks = retrieved_chunks[:k]
        retrieved_doc_ids = [c.document_id for c in top_k_chunks]

        expected_docs = set(test_case.expected_doc_ids)
        if not expected_docs:
            return {"hit": 1.0, "reciprocal_rank": 1.0, "precision": 1.0, "recall": 1.0}

        hits = [doc_id for doc_id in retrieved_doc_ids if doc_id in expected_docs]
        hit_rate = 1.0 if len(hits) > 0 else 0.0
        precision = len(hits) / float(k) if k > 0 else 0.0
        recall = len(hits) / float(len(expected_docs)) if len(expected_docs) > 0 else 0.0

        # Calculate Reciprocal Rank
        reciprocal_rank = 0.0
        for rank, doc_id in enumerate(retrieved_doc_ids, start=1):
            if doc_id in expected_docs:
                reciprocal_rank = 1.0 / rank
                break

        return {
            "hit": hit_rate,
            "reciprocal_rank": reciprocal_rank,
            "precision": precision,
            "recall": recall,
        }

    def evaluate_batch(self, results_pair: List[tuple[EvalTestCase, List[Chunk]]], k: int = 5) -> RetrievalEvalResult:
        """Evaluate a batch of (test_case, retrieved_chunks) pairs."""
        if not results_pair:
            return RetrievalEvalResult(total_queries=0, precision_at_k=0.0, recall_at_k=0.0, mrr=0.0, hit_rate=0.0, k=k)

        total_prec = 0.0
        total_rec = 0.0
        total_mrr = 0.0
        total_hits = 0.0

        for tc, retrieved in results_pair:
            metrics = self.evaluate_test_case(tc, retrieved, k=k)
            total_hits += metrics["hit"]
            total_mrr += metrics["reciprocal_rank"]
            total_prec += metrics["precision"]
            total_rec += metrics["recall"]

        n = len(results_pair)
        return RetrievalEvalResult(
            total_queries=n,
            precision_at_k=total_prec / n,
            recall_at_k=total_rec / n,
            mrr=total_mrr / n,
            hit_rate=total_hits / n,
            k=k,
        )

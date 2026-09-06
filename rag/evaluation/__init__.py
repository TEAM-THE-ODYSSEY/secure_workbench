"""
Evaluation package for retrieval metrics, relevance scoring, and benchmark datasets.
"""

from rag.evaluation.test_dataset import EvalTestCase, EvaluationDataset
from rag.evaluation.retrieval_eval import RetrievalEvaluator, RetrievalEvalResult
from rag.evaluation.relevance_eval import RelevanceEvaluator, RelevanceEvalResult

__all__ = [
    "EvalTestCase",
    "EvaluationDataset",
    "RetrievalEvaluator",
    "RetrievalEvalResult",
    "RelevanceEvaluator",
    "RelevanceEvalResult",
]

"""
Evaluation test dataset models for RAG benchmarking.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class EvalTestCase(BaseModel):
    """Test case schema for evaluating retrieval accuracy."""
    test_id: str
    query: str
    expected_doc_ids: List[str] = Field(default_factory=list)
    expected_chunk_ids: List[str] = Field(default_factory=list)
    filter_conditions: Dict[str, Any] = Field(default_factory=dict)
    ground_truth_answer: Optional[str] = None


class EvaluationDataset(BaseModel):
    """Collection of evaluation test cases."""
    name: str = "MRPL RAG Benchmark"
    test_cases: List[EvalTestCase] = Field(default_factory=list)

    def save_to_file(self, filepath: str) -> None:
        """Export dataset to JSON file."""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=2))

    @classmethod
    def load_from_file(cls, filepath: str) -> "EvaluationDataset":
        """Load dataset from JSON file."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)

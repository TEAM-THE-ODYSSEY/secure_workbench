from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Set


class BaseAgent(ABC):
    """Abstract Base Agent with formal capability contracts (Section 6)."""
    name: str = "base_agent"
    task_types: List[str] = []
    capabilities: Set[str] = set()
    input_types: List[str] = ["text"]
    output_types: List[str] = ["text"]
    required_tools: List[str] = []
    validator_chain: List[str] = ["text"]

    def __init__(self, llm):
        self.llm = llm

    def is_qualified_for(self, required_capabilities: Set[str]) -> bool:
        return required_capabilities.issubset(self.capabilities)

    @abstractmethod
    def run(self, user_text: str, context: str, model: str, metadata: dict[str, Any]) -> str:
        raise NotImplementedError

    def execute_task(
        self,
        directive: str,
        context: str,
        model: str,
        metadata: dict[str, Any],
    ) -> Dict[str, Any]:
        """High-level execution method returning answer, execution_result, and evidence."""
        answer = self.run(user_text=directive, context=context, model=model, metadata=metadata)
        return {
            "answer": answer,
            "execution_result": None,
            "evidence": [],
            "warnings": [],
        }

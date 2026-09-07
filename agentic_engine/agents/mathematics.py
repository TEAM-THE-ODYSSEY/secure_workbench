from __future__ import annotations

from typing import Any, Dict, List, Set
from .base import BaseAgent
from ..models.capabilities import TaskCapability


class MathematicalAgent(BaseAgent):
    name = "mathematics"
    task_types = ["mathematical"]
    capabilities: Set[str] = {
        TaskCapability.MATHEMATICS.value,
        TaskCapability.REASONING.value,
    }
    input_types = ["text"]
    output_types = ["text"]
    required_tools = []
    validator_chain = ["math"]

    def run(
        self,
        user_text: str,
        context: str = "",
        model: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        prompt = f"""You are a specialized mathematical reasoning agent.
Solve the user's mathematical task step-by-step.
State variables, identify formulas, perform substitution, calculate the result,
and verify your answer before outputting.

USER REQUEST:
{user_text}

CONTEXT:
{context or '[none]'}

MATHEMATICAL SOLUTION:
"""
        return self.llm.generate(prompt=prompt, model=model)


# Compatibility alias
MathematicsAgent = MathematicalAgent

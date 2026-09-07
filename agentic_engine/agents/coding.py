from __future__ import annotations

from typing import Any, Dict, List, Set
from .base import BaseAgent
from ..code_runner import CodingWorkflow
from ..models.capabilities import TaskCapability
from ..sandbox import DockerSandbox


class CodingAgent(BaseAgent):
    name = "coding"
    task_types = ["coding"]
    capabilities: Set[str] = {
        TaskCapability.CODING.value,
        TaskCapability.SANDBOX.value,
        TaskCapability.STRUCTURED_OUTPUT.value,
    }
    input_types = ["text"]
    output_types = ["text", "code", "xlsx", "csv"]
    required_tools = ["python_sandbox"]
    validator_chain = ["syntax", "code"]

    def __init__(self, llm, sandbox: DockerSandbox | None = None):
        super().__init__(llm)
        self.sandbox = sandbox or DockerSandbox()
        self.workflow = CodingWorkflow(self.llm, sandbox=self.sandbox)

    def run(
        self,
        user_text: str,
        context: str = "",
        model: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        res = self.execute_task(directive=user_text, context=context, model=model, metadata=metadata or {})
        return res["answer"]

    def execute_task(
        self,
        directive: str,
        context: str,
        model: str,
        metadata: dict[str, Any],
    ) -> Dict[str, Any]:
        result = self.workflow.run(directive, context, model)
        return {
            "answer": result.final_explanation,
            "execution_result": result.execution,
            "evidence": [{"type": "code_execution", "code": result.code, "success": result.execution.success if result.execution else False}],
            "warnings": [] if (result.execution and result.execution.success) else ["Sandbox execution encountered errors or fallback."],
        }

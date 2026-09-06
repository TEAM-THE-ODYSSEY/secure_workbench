from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ExecutionPlanState:
    task_type: str = "reasoning"
    task_reason: str = ""
    complexity: str = "small"
    agent: str = "reasoning"
    retrieval: bool = False
    tools: list[str] = field(default_factory=list)
    output_type: str = "text"
    validation_type: str = "text"
    max_iterations: int = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationState:
    valid: bool = False
    reason: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AgentState:
    chat_id: str
    user_request: str = ""
    file_path: str | None = None
    file_content: str = ""
    history: list[dict[str, Any]] = field(default_factory=list)
    retrieved_context: list[dict[str, Any]] = field(default_factory=list)

    plan: ExecutionPlanState = field(default_factory=ExecutionPlanState)

    selected_model: str = ""
    model_parameters: dict[str, Any] = field(default_factory=dict)

    current_step: str = "start"
    iteration: int = 0
    answer: str = ""
    execution_result: Any = None
    validation: ValidationState = field(default_factory=ValidationState)
    output_file: str | None = None
    status: str = "started"
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        # ExecutionResult is a dataclass in the sandbox; convert when possible.
        if self.execution_result is not None and hasattr(self.execution_result, "__dict__"):
            data["execution_result"] = dict(self.execution_result.__dict__)
        return data

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Set


@dataclass
class DAGNodeDefinition:
    node_id: str
    node_type: str  # "tool", "agent", "validation", "synthesis"
    target: str     # tool name or agent name
    dependencies: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    retry_policy: Dict[str, Any] = field(default_factory=lambda: {"max_retries": 2, "backoff": 1.0})
    timeout_seconds: float = 30.0
    status: str = "PENDING"
    result: Any = None
    error: Optional[str] = None


@dataclass
class ExecutionPlan:
    """Formal, inspectable, and logged contract for agentic execution."""
    plan_id: str
    task_type: str
    complexity: str
    capabilities: List[str] = field(default_factory=list)
    domain: str = "general"
    agent: str = "reasoning"
    model_policy: str = "balanced"
    tools: List[str] = field(default_factory=list)
    validator_chain: List[str] = field(default_factory=list)
    output_type: str = "text"
    validation_type: str = "text"
    retrieval: bool = False
    context_policy: str = "task_scoped"
    max_iterations: int = 1
    max_retries: int = 2
    max_tool_calls: int = 4
    timeout_seconds: float = 60.0
    priority: int = 1
    dag_nodes: List[DAGNodeDefinition] = field(default_factory=list)
    task_reason: str = ""

    def __post_init__(self):
        if not self.validation_type and self.validator_chain:
            self.validation_type = self.validator_chain[0]
        elif self.validation_type and not self.validator_chain:
            self.validator_chain = [self.validation_type]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Compatibility alias for existing codebase
ExecutionPlanState = ExecutionPlan

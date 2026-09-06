from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field

from .task import TaskStatus


class StepRecord(BaseModel):
    """One iteration of an agent's think/act loop — kept for transparency
    and debugging, and so the orchestrator/UI can show iterative progress."""

    step_index: int
    thought: Optional[str] = None
    tool_called: Optional[str] = None
    tool_input: Optional[Any] = None
    tool_output: Optional[Any] = None
    error: Optional[str] = None


class AgentResponse(BaseModel):
    task_id: str
    agent_name: str
    status: TaskStatus
    content: str
    steps: List[StepRecord] = Field(default_factory=list)
    error: Optional[str] = None

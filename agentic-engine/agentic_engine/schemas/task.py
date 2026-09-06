from __future__ import annotations

import uuid
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class Task(BaseModel):
    """
    A unit of work sent into the Agentic Engine.

    `agent_type` is explicit for now (no auto-router yet) — the caller
    decides which agent should handle the task, e.g. "reasoning" or
    "mathematical". This keeps the engine usable standalone while the
    Task Router is built out later.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    input_text: str
    agent_type: str = "reasoning"
    context: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    max_steps: int = 6
    status: TaskStatus = TaskStatus.PENDING

from __future__ import annotations

from typing import Dict, Optional

from ..schemas.response import AgentResponse
from ..schemas.task import Task, TaskStatus


class TaskStateStore:
    """
    Minimal in-memory store for task + latest response, keyed by task id.

    Kept deliberately simple (no DB, no persistence) so it has zero
    coupling to whatever backend/storage the rest of the workbench uses.
    If persistence is needed later, swap this class's internals for a
    DB-backed implementation without touching the orchestrator's calls
    into it.
    """

    def __init__(self):
        self._tasks: Dict[str, Task] = {}
        self._responses: Dict[str, AgentResponse] = {}

    def register(self, task: Task) -> None:
        task.status = TaskStatus.PENDING
        self._tasks[task.id] = task

    def mark_running(self, task_id: str) -> None:
        if task_id in self._tasks:
            self._tasks[task_id].status = TaskStatus.RUNNING

    def record_result(self, task_id: str, response: AgentResponse) -> None:
        if task_id in self._tasks:
            self._tasks[task_id].status = response.status
        self._responses[task_id] = response

    def get_task(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def get_response(self, task_id: str) -> Optional[AgentResponse]:
        return self._responses.get(task_id)

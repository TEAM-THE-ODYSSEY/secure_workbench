"""
Task Manager for MRPL Sovereign AI Workbench.
Tracks active task lifecycle and handles asynchronous cancellation requests.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging
from typing import Dict, List, Optional

logger = logging.getLogger("agent.task_manager")


class TaskStatus(str, Enum):
    QUEUED = "QUEUED"
    PLANNING = "PLANNING"
    RUNNING = "RUNNING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    CANCEL_REQUESTED = "CANCEL_REQUESTED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


@dataclass
class TaskRecord:
    task_id: str
    user_id: str
    conversation_id: str
    status: TaskStatus = TaskStatus.QUEUED
    intent: str = "GENERAL"
    active_step: str = "START"
    completed_steps: List[str] = field(default_factory=list)
    partial_results: List[Dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error_message: Optional[str] = None


class TaskManager:
    """Central Task Manager tracking active multi-agent tasks and cancellation flags."""

    def __init__(self):
        self._tasks: Dict[str, TaskRecord] = {}

    def register_task(self, task_id: str, user_id: str, conversation_id: str) -> TaskRecord:
        record = TaskRecord(task_id=task_id, user_id=user_id, conversation_id=conversation_id)
        self._tasks[task_id] = record
        logger.info(f"Registered task '{task_id}' for user '{user_id}'")
        return record

    def update_status(self, task_id: str, status: TaskStatus, active_step: Optional[str] = None) -> None:
        if task_id in self._tasks:
            rec = self._tasks[task_id]
            rec.status = status
            if active_step:
                rec.active_step = active_step
            rec.updated_at = datetime.now(timezone.utc)
            logger.info(f"Task '{task_id}' status updated to {status.value} (step: {active_step})")

    def request_cancel(self, task_id: str, user_id: str) -> bool:
        """
        Request task cancellation if owned by current user.
        """
        if task_id not in self._tasks:
            return False
        rec = self._tasks[task_id]
        if rec.user_id != user_id and user_id != "admin":
            logger.warning(f"Unauthorized task cancellation request for '{task_id}' by user '{user_id}'")
            return False

        if rec.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.FAILED):
            return True  # Already terminal

        rec.status = TaskStatus.CANCEL_REQUESTED
        rec.updated_at = datetime.now(timezone.utc)
        logger.warning(f"Task '{task_id}' cancellation requested by user '{user_id}'.")
        return True

    def is_cancelled(self, task_id: str) -> bool:
        if task_id in self._tasks:
            return self._tasks[task_id].status in (TaskStatus.CANCEL_REQUESTED, TaskStatus.CANCELLED)
        return False

    def get_task(self, task_id: str) -> Optional[TaskRecord]:
        return self._tasks.get(task_id)


# Global singleton instance
task_manager = TaskManager()

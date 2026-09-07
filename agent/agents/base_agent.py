"""
Base Abstract Agent class for MRPL Sovereign AI Workbench.
Defines the standard execution interface for all specialized agents.
"""

from abc import ABC, abstractmethod
import logging
from typing import List, Optional
from agent.models.schemas import AgentResult, TaskContext

logger = logging.getLogger("agent.base")


class BaseAgent(ABC):
    """
    Abstract Base Class for all specialized capability agents.
    Contract: execute(task_context: TaskContext) -> AgentResult
    """

    def __init__(self, name: str, description: str, required_permissions: Optional[List[str]] = None):
        self.name = name
        self.description = description
        self.required_permissions = required_permissions or []

    def validate_permissions(self, context: TaskContext) -> bool:
        """Validate that the user/context possesses all required permissions."""
        if not self.required_permissions:
            return True
        user_perms = context.permissions or []
        # ADMIN role automatically bypasses permission check
        if context.role and context.role.upper() == "ADMIN":
            return True
        missing = [p for p in self.required_permissions if p not in user_perms]
        if missing:
            logger.warning(f"Agent '{self.name}' access denied for user '{context.user_id}': missing permissions {missing}")
            return False
        return True

    @abstractmethod
    def execute(self, context: TaskContext) -> AgentResult:
        """
        Execute bounded agent capability.
        Must return a standardized AgentResult object.
        """
        pass

"""
Service layer for Reasoning Mini-Agent V1.
Provides high-level entry points for executing tasks.
"""

import logging
from typing import Optional

from agent.models import AgentTaskResult, TaskRequest
from agent.state_machine import ReasoningStateMachine

logger = logging.getLogger("agent.service")


class ReasoningAgentService:
    """
    Service wrapper for the Reasoning State Machine.
    """

    def __init__(self, state_machine: Optional[ReasoningStateMachine] = None):
        self.state_machine = state_machine or ReasoningStateMachine()

    def process_task(self, request: TaskRequest, task_id: Optional[str] = None) -> AgentTaskResult:
        """
        Execute task request through Reasoning State Machine.
        """
        logger.info(f"ReasoningAgentService processing task objective: '{request.objective}'")
        result = self.state_machine.run(request=request, task_id=task_id)
        logger.info(f"ReasoningAgentService task {result.task_id} completed with status: {result.status}")
        return result


# Global singleton instance
agent_service = ReasoningAgentService()

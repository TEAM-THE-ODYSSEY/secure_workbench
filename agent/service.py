"""
Service wrapper facade for Main AI Agent.
Maintains 100% backward-compatible API entry points.
"""

import logging
from typing import Optional

from agent.models.schemas import AgentTaskResult, TaskRequest
from agent.main_agent import main_agent, MainAgent

logger = logging.getLogger("agent.service")


class ReasoningAgentService:
    """
    High-level Service facade delegating to the Main AI Agent.
    """

    def __init__(self, agent: Optional[MainAgent] = None, state_machine: Optional[Any] = None):
        if state_machine and not agent:
            agent = MainAgent(state_machine=state_machine)
        self.main_agent = agent or main_agent
        self.state_machine = self.main_agent.state_machine

    def process_task(self, request: TaskRequest, task_id: Optional[str] = None) -> AgentTaskResult:
        """Process task through Main AI Agent."""
        return self.main_agent.process_task(request=request, task_id=task_id)


# Global singleton facade
agent_service = ReasoningAgentService()

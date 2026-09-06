"""
Main AI Agent for MRPL Sovereign/Air-Gapped Agentic AI Workbench.
Single unified agent control layer orchestrating dynamic context planning,
capability tool selection, vLLM Qwen3-4B/1.7B reasoning, grounding verification, and PDF generation.
"""

import logging
from typing import Optional

from agent.models.model_manager import ModelManager
from agent.models.schemas import AgentTaskResult, TaskRequest
from agent.state_machine import MainAgentStateMachine
from agent.gateway.input_gateway import InputGateway

logger = logging.getLogger("agent.main_agent")


class MainAgent:
    """
    Main AI Agent control layer.
    """

    def __init__(
        self,
        state_machine: Optional[MainAgentStateMachine] = None,
        input_gateway: Optional[InputGateway] = None,
        model_manager: Optional[ModelManager] = None,
    ):
        self.model_manager = model_manager or ModelManager()
        self.state_machine = state_machine or MainAgentStateMachine(model_manager=self.model_manager)
        self.input_gateway = input_gateway or InputGateway()

    def process_task(
        self,
        request: TaskRequest,
        task_id: Optional[str] = None,
    ) -> AgentTaskResult:
        """
        Process user request through Main Agent control layer.
        """
        logger.info(f"MainAgent processing request: objective='{request.objective}', entities={request.entities}")
        result = self.state_machine.run(request=request, task_id=task_id)
        logger.info(f"MainAgent completed task '{result.task_id}' with status '{result.status}' (active_model={result.model}, fallback={result.fallback_used})")
        return result

    def health_check(self):
        """Return Main Agent and vLLM health status."""
        return self.model_manager.health_check()


# Singleton instance
main_agent = MainAgent()

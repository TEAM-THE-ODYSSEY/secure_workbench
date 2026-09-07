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


from agent.orchestrator import main_orchestrator


class MainAgent:
    """
    Main AI Agent control layer. Delegates to MainOrchestrator.
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
        user_id: str = "operator",
        conversation_id: str = "conv_default",
    ) -> AgentTaskResult:
        """
        Process user request through Main Orchestrator.
        """
        logger.info(f"MainAgent processing request: objective='{request.objective}', entities={request.entities}")
        result = main_orchestrator.process_task(request, task_id=task_id, user_id=user_id, conversation_id=conversation_id)
        logger.info(f"MainAgent completed task '{result.task_id}' with status '{result.status}' (model={result.model})")
        return result


    def health_check(self):
        """Return Main Agent and vLLM health status."""
        return self.model_manager.health_check()


# Singleton instance
main_agent = MainAgent()

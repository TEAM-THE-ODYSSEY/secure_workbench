"""
Centralized Agent Registry for MRPL Sovereign AI Workbench.
Registers, manages, and dispatches tasks to specialized capability agents.
"""

import logging
from typing import Dict, List, Optional
from agent.agents.base_agent import BaseAgent
from agent.models.schemas import AgentResult, TaskContext

logger = logging.getLogger("agent.registry")


from agent.agents.general_agent import GeneralAgent
from agent.agents.knowledge_agent import KnowledgeAgent
from agent.agents.document_agent import DocumentAgent
from agent.agents.pid_agent import PIDAgent
from agent.agents.coding_agent import CodingAgent
from agent.agents.report_agent import ReportAgent


class AgentRegistry:
    """
    Central Agent Registry managing specialized agents:
    - general
    - knowledge
    - document
    - pid
    - coding
    - report
    """

    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        self._register_default_agents()

    def _register_default_agents(self):
        """Register core specialized capability agents."""
        self.register(GeneralAgent())
        self.register(KnowledgeAgent())
        self.register(DocumentAgent())
        self.register(PIDAgent())
        self.register(CodingAgent())
        self.register(ReportAgent())


    def register(self, agent: BaseAgent) -> None:
        """Register a specialized agent instance."""
        self._agents[agent.name] = agent
        logger.info(f"AgentRegistry registered agent capability '{agent.name}': {agent.description}")

    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Retrieve agent by capability name."""
        return self._agents.get(name.lower())

    def list_agents(self) -> List[Dict[str, str]]:
        """List registered agents with descriptions."""
        return [
            {
                "name": agent.name,
                "description": agent.description,
                "permissions": ", ".join(agent.required_permissions),
            }
            for agent in self._agents.values()
        ]

    def execute_agent(self, agent_name: str, context: TaskContext) -> AgentResult:
        """
        Validate authorization and execute agent.
        """
        agent = self.get_agent(agent_name)
        if not agent:
            return AgentResult(
                agent=agent_name,
                status="failure",
                errors=[f"Agent '{agent_name}' is not registered in AgentRegistry."],
            )

        if not agent.validate_permissions(context):
            return AgentResult(
                agent=agent_name,
                status="failure",
                errors=[f"Permission denied for agent '{agent_name}'."],
            )

        try:
            logger.info(f"Executing agent '{agent.name}' for task '{context.task_id}' (user='{context.user_id}')")
            return agent.execute(context)
        except Exception as e:
            logger.error(f"Error executing agent '{agent.name}': {e}", exc_info=True)
            return AgentResult(
                agent=agent.name,
                status="failure",
                errors=[f"Execution exception in agent '{agent.name}': {str(e)}"],
            )


# Global singleton instance
agent_registry = AgentRegistry()

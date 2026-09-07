"""
Main AI Agent Package for MRPL Sovereign/Air-Gapped Agentic AI Workbench.
"""

from agent.main_agent import MainAgent, main_agent
from agent.service import agent_service
from agent.models.schemas import TaskRequest, AgentTaskResult
from agent.models.model_manager import ModelManager
from agent.tools.knowledge_tool import KnowledgeTool
from agent.tools.pid_tool import PIDTool
from agent.tools.registry import ToolRegistry

__all__ = [
    "MainAgent",
    "main_agent",
    "agent_service",
    "TaskRequest",
    "AgentTaskResult",
    "ModelManager",
    "KnowledgeTool",
    "PIDTool",
    "ToolRegistry",
]

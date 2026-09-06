"""
Capability Tool Registry for Main AI Agent.
Registers, validates, and dispatches tool execution requests.
"""

import logging
from typing import Any, Callable, Dict, List, Optional
from agent.tools.base import BaseTool
from agent.tools.knowledge_tool import KnowledgeTool
from agent.tools.pid_tool import PIDTool
from agent.tools.document_tool import DocumentTool
from agent.tools.data_tool import DataAnalysisTool
from agent.tools.report_tool import ReportTool

logger = logging.getLogger("agent.tools.registry")


class ToolRegistry:
    """
    Capability Tool Registry managing KnowledgeTool, PIDTool, DocumentTool, DataAnalysisTool, and ReportTool.
    """

    def __init__(self, knowledge_tool: Optional[KnowledgeTool] = None):
        self._tools: Dict[str, BaseTool] = {}
        self._register_default_tools()
        if knowledge_tool:
            self.register(knowledge_tool)

    def _register_default_tools(self):
        """Register default core capability tools."""
        self.register(KnowledgeTool())
        self.register(PIDTool())
        self.register(DocumentTool())
        self.register(DataAnalysisTool())
        self.register(ReportTool())

    def register(self, tool: BaseTool) -> None:
        """Register a capability tool instance."""
        self._tools[tool.name] = tool
        logger.info(f"Registered tool capability '{tool.name}': {tool.description}")

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Retrieve tool by capability name."""
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, str]]:
        """Return list of available tools with names and descriptions for LLM planner."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
            }
            for tool in self._tools.values()
        ]

    def execute(self, name: str, **kwargs) -> Any:
        """Validate and execute tool call."""
        tool = self.get_tool(name)
        if not tool:
            # Fallback for knowledge_search alias
            if name in ("knowledge.search", "knowledge_search"):
                tool = self.get_tool("knowledge_search")
            elif name in ("pid.query", "pid_query", "pid"):
                tool = self.get_tool("pid_query")

        if not tool:
            raise ValueError(f"Tool '{name}' is not registered in ToolRegistry. Available: {list(self._tools.keys())}")

        logger.info(f"ToolRegistry executing capability '{tool.name}' with kwargs keys: {list(kwargs.keys())}")
        return tool.execute(**kwargs)

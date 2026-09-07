from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from .base import BaseTool, ToolExecutionRecord
from .document_tool import DocumentExporterTool
from .pid_tool import PIDTool
from .sandbox_tool import SandboxTool

logger = logging.getLogger("agentic_engine.tools.registry")


class ToolNotPermittedError(PermissionError):
    pass


class ToolRegistry:
    """Manages tool instances, enforces per-agent allowlists, and logs tool execution traces."""

    def __init__(self):
        self._tools: Dict[str, Any] = {
            "python_sandbox": SandboxTool(),
            "document_exporter": DocumentExporterTool(),
            "pid_tool": PIDTool(),
        }
        self._execution_history: List[ToolExecutionRecord] = []

    def register_tool(self, name: str, tool: Any) -> None:
        self._tools[name.lower()] = tool

    def get_tool(self, name: str) -> Optional[Any]:
        return self._tools.get(name.lower())

    def execute_tool(
        self,
        tool_name: str,
        agent_name: str,
        allowlist: Optional[List[str]] = None,
        **kwargs,
    ) -> ToolExecutionRecord:
        """Executes a tool under policy enforcement, recording telemetry."""
        if allowlist is not None and tool_name.lower() not in [a.lower() for a in allowlist]:
            raise ToolNotPermittedError(
                f"Agent '{agent_name}' is not authorized to invoke tool '{tool_name}'."
            )

        tool = self.get_tool(tool_name)
        if tool is None:
            raise ValueError(f"Tool '{tool_name}' is not registered in ToolRegistry.")

        if hasattr(tool, "run"):
            record = tool.run(**kwargs)
        else:
            # Wrap callable
            from .base import BaseTool
            record = BaseTool.run(tool, **kwargs)

        self._execution_history.append(record)
        return record

    @property
    def history(self) -> List[ToolExecutionRecord]:
        return list(self._execution_history)

from __future__ import annotations

from ..sandbox.executor import SandboxExecutor
from ..schemas.tool import ToolResult

TOOL_NAME = "python_tool"


class PythonTool:
    """
    Agent-facing wrapper around SandboxExecutor.

    Agents call `run(code)` and get back a ToolResult they can feed
    into their next reasoning step — they never touch subprocess/
    resource limits directly.
    """

    name = TOOL_NAME
    description = (
        "Executes a Python code snippet in an isolated sandbox and returns "
        "stdout/stderr. Use this for any calculation, data manipulation, or "
        "verification instead of computing it in your head."
    )

    def __init__(self, executor: SandboxExecutor | None = None):
        self.executor = executor or SandboxExecutor()

    def run(self, code: str) -> ToolResult:
        result = self.executor.execute(code)

        if result.timed_out:
            return ToolResult(
                tool_name=self.name,
                success=False,
                output=result.stdout,
                error="Execution timed out.",
            )

        if result.success:
            return ToolResult(
                tool_name=self.name,
                success=True,
                output=result.stdout.strip(),
                error=result.stderr.strip() or None,
            )

        return ToolResult(
            tool_name=self.name,
            success=False,
            output=result.stdout.strip() or None,
            error=result.stderr.strip() or f"Process exited with code {result.returncode}",
        )

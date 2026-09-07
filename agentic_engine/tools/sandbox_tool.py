from __future__ import annotations

from typing import Any, Dict, Optional
from .base import BaseTool
from ..sandbox import DockerSandbox, ExecutionResult


class SandboxTool(BaseTool):
    """Traceable wrapper around DockerSandbox."""
    name = "python_sandbox"
    description = "Executes Python code in an isolated, resource-bounded Docker container."

    def __init__(self, sandbox: Optional[DockerSandbox] = None):
        self.sandbox = sandbox or DockerSandbox()

    def _execute(self, code: str, timeout: int = 15, **kwargs) -> Dict[str, Any]:
        result: ExecutionResult = self.sandbox.run(code=code, timeout=timeout)
        return {
            "success": result.success,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.exit_code,
            "duration": result.duration,
        }

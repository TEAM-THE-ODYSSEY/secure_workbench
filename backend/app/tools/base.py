"""
BaseTool abstract class definition for Main AI Agent capability tools.
Ensures tool security: evidence is strictly DATA/EVIDENCE, no code/SQL execution.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel


class BaseTool(ABC):
    """
    Abstract interface for deterministic capability tools.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool name."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable tool description."""
        pass

    @property
    def permission_metadata(self) -> Dict[str, Any]:
        """Tool risk/permission metadata."""
        return {
            "read_only": True,
            "requires_auth": False,
            "executable_code": False,
        }

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """Execute deterministic tool logic with controlled schema parameters."""
        pass

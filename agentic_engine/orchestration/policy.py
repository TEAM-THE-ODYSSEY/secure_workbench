from __future__ import annotations

from typing import Dict, List, Set, Tuple


class PolicyViolationError(PermissionError):
    """Raised when an operation violates security, tool, or resource policies."""
    pass


class PolicyEngine:
    """Enforces execution boundaries, tool allowlists, model authorizations,
    and resource safety limits.
    """

    ALLOWED_AGENTS: Set[str] = {
        "reasoning",
        "mathematics",
        "coding",
        "document",
        "multimodal",
        "pid",
    }

    ALLOWED_OUTPUT_TYPES: Set[str] = {
        "text",
        "json",
        "csv",
        "xlsx",
        "docx",
        "pdf",
    }

    # Strict Per-Agent Tool Allowlists
    AGENT_TOOL_ALLOWLIST: Dict[str, Set[str]] = {
        "reasoning": {"knowledge_retriever"},
        "mathematics": set(),
        "coding": {"python_sandbox"},
        "document": {"document_parser", "knowledge_retriever"},
        "multimodal": {"ocr", "document_parser", "pid_engine"},
        "pid": {"ocr", "pid_engine"},
    }

    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode

    def validate_agent(self, agent_name: str) -> Tuple[bool, str]:
        if agent_name.lower() not in self.ALLOWED_AGENTS:
            return False, f"Agent '{agent_name}' is not in the allowed agent registry."
        return True, "allowed"

    def validate_tool_access(self, agent_name: str, tool_name: str) -> Tuple[bool, str]:
        allowed_tools = self.AGENT_TOOL_ALLOWLIST.get(agent_name.lower(), set())
        if tool_name.lower() not in allowed_tools:
            return False, f"Tool '{tool_name}' is not permitted for agent '{agent_name}' (Allowed: {allowed_tools})."
        return True, "allowed"

    def filter_allowed_tools(self, agent_name: str, requested_tools: List[str]) -> List[str]:
        allowed = self.AGENT_TOOL_ALLOWLIST.get(agent_name.lower(), set())
        return [t for t in requested_tools if t.lower() in allowed]

    def validate_output_type(self, output_type: str) -> Tuple[bool, str]:
        if output_type.lower() not in self.ALLOWED_OUTPUT_TYPES:
            return False, f"Output format '{output_type}' is not authorized."
        return True, "allowed"

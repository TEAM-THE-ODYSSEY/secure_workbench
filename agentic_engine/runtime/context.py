from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ScopedContext:
    """Task-scoped context delivering only relevant slices to agents and tools."""
    request_id: str
    session_id: str
    task_context: str = ""
    conversation_context: List[Dict[str, Any]] = field(default_factory=list)
    retrieved_context: List[Dict[str, Any]] = field(default_factory=list)
    tool_context: Dict[str, Any] = field(default_factory=dict)
    evidence_context: List[Dict[str, Any]] = field(default_factory=list)
    previous_attempt_context: Optional[str] = None
    file_path: Optional[str] = None
    file_content: Optional[str] = None

    def for_agent(self, agent_name: str, max_chars: int = 16384) -> str:
        """Constructs an agent-specific scoped context string."""
        parts = []

        if self.task_context:
            parts.append(f"TASK DIRECTIVE:\n{self.task_context}")

        if self.file_content and agent_name in {"document", "multimodal", "pid"}:
            preview = self.file_content[:max_chars]
            parts.append(f"DOCUMENT EXTRACT:\n{preview}")

        if self.retrieved_context:
            retrieved_str = "\n".join(
                f"- {item.get('text', item.get('content', ''))}"
                for item in self.retrieved_context[:5]
            )
            parts.append(f"GROUNDED KNOWLEDGE:\n{retrieved_str}")

        if self.evidence_context and agent_name in {"pid", "reasoning", "multimodal"}:
            import json
            parts.append(f"VERIFIED EVIDENCE:\n{json.dumps(self.evidence_context[:20], indent=2)}")

        if self.previous_attempt_context:
            parts.append(f"PREVIOUS VALIDATION FEEDBACK:\n{self.previous_attempt_context}")

        return "\n\n".join(parts)

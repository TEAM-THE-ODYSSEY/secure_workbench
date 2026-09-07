from __future__ import annotations

import logging
from typing import Dict, List, Optional, Set

from ..models.capabilities import TaskCapability

logger = logging.getLogger("agentic_engine.router")


class AgentNotQualifiedError(RuntimeError):
    """Raised when no registered agent possesses the required capabilities."""
    pass


class CapabilityRouter:
    """Capability-first router that resolves task requirements against agent capability contracts."""

    # Canonical mapping of task types to foundational capabilities
    TASK_CAPABILITY_MAP: Dict[str, Set[str]] = {
        "reasoning": {
            TaskCapability.REASONING.value,
        },
        "mathematics": {
            TaskCapability.MATHEMATICS.value,
            TaskCapability.REASONING.value,
        },
        "coding": {
            TaskCapability.CODING.value,
            TaskCapability.SANDBOX.value,
        },
        "document": {
            TaskCapability.DOCUMENT.value,
            TaskCapability.STRUCTURED_OUTPUT.value,
        },
        "multimodal": {
            TaskCapability.MULTIMODAL.value,
            TaskCapability.OCR.value,
        },
        "pid": {
            TaskCapability.VISION.value,
            TaskCapability.OCR.value,
            TaskCapability.PID_ANALYSIS.value,
            TaskCapability.TOPOLOGY.value,
            TaskCapability.EVIDENCE.value,
            TaskCapability.STRUCTURED_OUTPUT.value,
        },
    }

    def resolve_required_capabilities(
        self,
        task_type: str,
        retrieval_requested: bool = False,
        wants_structured_output: bool = False,
    ) -> Set[str]:
        caps = set(self.TASK_CAPABILITY_MAP.get(task_type.lower(), {TaskCapability.REASONING.value}))
        if retrieval_requested:
            caps.add(TaskCapability.RETRIEVAL.value)
        if wants_structured_output:
            caps.add(TaskCapability.STRUCTURED_OUTPUT.value)
        return caps

    def route_agent(
        self,
        required_capabilities: Set[str],
        agent_registry: Dict[str, Any],
        preferred_agent: Optional[str] = None,
    ) -> str:
        """Finds qualified agent where required_capabilities ⊆ agent.capabilities."""
        qualified_agents = []

        for name, agent in agent_registry.items():
            agent_caps = getattr(agent, "capabilities", set())
            if isinstance(agent_caps, (list, tuple)):
                agent_caps = set(agent_caps)

            # Check subset relation: required ⊆ agent
            if required_capabilities.issubset(agent_caps):
                qualified_agents.append(name)

        if not qualified_agents:
            # Fall back to best overlap if exact subset isn't satisfied
            scored = []
            for name, agent in agent_registry.items():
                agent_caps = set(getattr(agent, "capabilities", set()))
                overlap = len(required_capabilities.intersection(agent_caps))
                if overlap > 0:
                    scored.append((overlap, name))
            scored.sort(reverse=True)
            if scored:
                qualified_agents = [scored[0][1]]

        if not qualified_agents:
            raise AgentNotQualifiedError(
                f"AGENT_NOT_QUALIFIED: No registered agent satisfies capabilities: {required_capabilities}"
            )

        if preferred_agent and preferred_agent in qualified_agents:
            return preferred_agent

        return qualified_agents[0]

"""
Skill Registry for MRPL Sovereign AI Workbench.
Manages domain workflow skills alongside specialized agents.
"""

from dataclasses import dataclass, field
import logging
from typing import Any, Callable, Dict, List, Optional
from agent.models.schemas import TaskContext

logger = logging.getLogger("skills.registry")


@dataclass
class DomainSkill:
    """Structured domain skill workflow definition."""
    name: str
    description: str
    required_inputs: List[str]
    allowed_agents: List[str]
    allowed_tools: List[str]
    workflow_handler: Callable[[TaskContext], Dict[str, Any]]
    required_permissions: List[str] = field(default_factory=list)
    output_format: str = "TEXT"


class SkillRegistry:
    """Central Skill Registry managing domain skills."""

    def __init__(self):
        self._skills: Dict[str, DomainSkill] = {}
        self._load_defaults()

    def _load_defaults(self):
        try:
            from skills.loader import load_builtin_skills
            load_builtin_skills()
        except Exception as e:
            logger.debug(f"Notice auto-loading skills: {e}")

    def register(self, skill: DomainSkill) -> None:
        """Register a domain skill."""
        self._skills[skill.name] = skill
        logger.info(f"SkillRegistry registered skill '{skill.name}': {skill.description}")

    def get_skill(self, name: str) -> Optional[DomainSkill]:
        """Retrieve skill by name."""
        return self._skills.get(name.lower())

    def list_skills(self) -> List[Dict[str, Any]]:
        """List registered skills."""
        return [
            {
                "name": skill.name,
                "description": skill.description,
                "required_inputs": skill.required_inputs,
                "allowed_agents": skill.allowed_agents,
            }
            for skill in self._skills.values()
        ]

    def discover_skill(self, query: str) -> Optional[DomainSkill]:
        """
        Auto-discover matching domain skill based on user query keywords.
        """
        if not self._skills:
            try:
                from skills.loader import load_builtin_skills
                load_builtin_skills()
            except Exception:
                pass

        q_lower = query.lower()
        if any(kw in q_lower for kw in ["shutdown", "unit stop", "trip sequence", "shutdown sop"]):
            return self.get_skill("shutdown_sop")
        if any(kw in q_lower for kw in ["vibration", "bearing", "failure analysis", "tripped", "cavitation"]):
            return self.get_skill("equipment_failure")
        if any(kw in q_lower for kw in ["downstream", "upstream", "p&id", "pid", "isolation valve"]):
            return self.get_skill("pid_topology")
        if any(kw in q_lower for kw in ["calculate", "pump efficiency", "efficiency", "throughput variance", "efficiency calculation"]):
            return self.get_skill("pump_efficiency")
        if any(kw in q_lower for kw in ["compare document", "compare pdf", "compare sop"]):
            return self.get_skill("document_comparison")
        if any(kw in q_lower for kw in ["summarize", "key findings", "executive summary"]):
            return self.get_skill("document_summary")
        if any(kw in q_lower for kw in ["action items", "next steps", "task list"]):
            return self.get_skill("action_items")
        if any(kw in q_lower for kw in ["report pdf", "create pdf", "generate report"]):
            return self.get_skill("technical_report")
        return None

    def find_matching_skills(self, query: str) -> List[DomainSkill]:
        """Find matching skills for a query (alias for discover_skill returning list)."""
        if not self._skills:
            try:
                from skills.loader import load_builtin_skills
                load_builtin_skills()
            except Exception:
                pass
        skill = self.discover_skill(query)
        if skill:
            return [skill]
        q_lower = query.lower()
        matched = []
        for s in self._skills.values():
            if s.name.lower() in q_lower or any(w in q_lower for w in s.name.split("_") if len(w) > 2):
                matched.append(s)
        return matched


# Global singleton instance
skill_registry = SkillRegistry()

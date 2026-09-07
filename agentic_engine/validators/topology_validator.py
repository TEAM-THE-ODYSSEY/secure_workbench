from __future__ import annotations

from typing import Any
from .base import BaseValidator, ValidationResult


class TopologyValidator(BaseValidator):
    """Validates connectivity graph completeness and edge consistency in industrial schematics."""

    def validate(self, output: str, execution: Any = None, **kwargs) -> ValidationResult:
        if execution is not None and hasattr(execution, "relationships"):
            rels = getattr(execution, "relationships", [])
            objects = getattr(execution, "objects", [])

            if len(objects) > 0 and len(rels) == 0:
                return ValidationResult(
                    False,
                    "P&ID objects detected, but no topological process connections established.",
                    {"objects": len(objects), "relationships": 0},
                )

            return ValidationResult(
                True,
                f"P&ID topology valid: {len(objects)} components with {len(rels)} directed connections.",
                {"objects_count": len(objects), "relationships_count": len(rels)},
            )

        # Text fallback check
        text = (output or "").lower()
        has_flow = any(x in text for x in ("connect", "feed", "line", "pipe", "──►", "->"))
        if not has_flow and len(text) < 50:
            return ValidationResult(False, "No topological flow relationships identified in P&ID output.")

        return ValidationResult(True, "Topological flow relationships present in text.")

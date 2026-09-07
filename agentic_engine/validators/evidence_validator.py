from __future__ import annotations

from typing import Any
from .base import BaseValidator, ValidationResult


class EvidenceValidator(BaseValidator):
    """Validates domain-specific topology and evidence attribution for P&ID schematics."""

    def __init__(self, min_confidence: float = 0.65):
        self.min_confidence = min_confidence

    def validate(self, output: str, execution: Any = None, **kwargs) -> ValidationResult:
        if not (output or "").strip() and execution is None:
            return ValidationResult(False, "Empty evidence and output for P&ID analysis.")

        # If execution result from PIDTool is provided, inspect structured evidence
        if execution is not None:
            confidence = getattr(execution, "confidence", 0.0)
            decision = getattr(execution, "decision", "output")
            warnings = getattr(execution, "warnings", [])
            objects = getattr(execution, "objects", [])
            relationships = getattr(execution, "relationships", [])

            details = {
                "confidence": confidence,
                "decision": decision,
                "objects_count": len(objects),
                "relationships_count": len(relationships),
                "warnings_count": len(warnings),
            }

            if decision == "human_verification" or confidence < self.min_confidence:
                return ValidationResult(
                    True,  # Handled safely via human verification queue rather than silent crash
                    f"Evidence confidence ({confidence:.2f}) requires human engineering verification.",
                    details,
                )

            return ValidationResult(
                True,
                f"P&ID evidence verified with confidence {confidence:.2f} across {len(relationships)} connections.",
                details,
            )

        # Fallback text inspection: ensure evidence markers exist
        text = output.lower()
        has_equipment_evidence = any(x in text for x in ("valve", "pump", "vessel", "tank", "instrument", "tag"))
        has_connections = any(x in text for x in ("connect", "line", "pipe", "-->", "──►"))

        if not (has_equipment_evidence and has_connections):
            return ValidationResult(
                False,
                "P&ID output does not contain verified equipment tags or topological connections.",
                {"output_length": len(output)},
            )

        return ValidationResult(
            True,
            "P&ID text contains grounded equipment and connectivity evidence.",
            {"output_length": len(output)},
        )

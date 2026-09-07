from __future__ import annotations

from typing import Any, List, Optional
from .base import BaseValidator, ValidationResult


class ValidatorChain(BaseValidator):
    """Composes multiple specialized validators into a sequential verification chain."""

    def __init__(self, validators: List[BaseValidator]):
        self.validators = validators

    def validate(self, output: str, **kwargs) -> ValidationResult:
        combined_details = {}
        failure_reasons = []

        for idx, validator in enumerate(self.validators, start=1):
            res = validator.validate(output, **kwargs)
            val_name = validator.__class__.__name__
            combined_details[f"{idx}_{val_name}"] = res.details or {}

            if not res.valid:
                failure_reasons.append(f"[{val_name}] {res.reason}")

        if failure_reasons:
            return ValidationResult(
                valid=False,
                reason="; ".join(failure_reasons),
                details=combined_details,
            )

        return ValidationResult(
            valid=True,
            reason=f"All {len(self.validators)} validators in chain satisfied.",
            details=combined_details,
        )

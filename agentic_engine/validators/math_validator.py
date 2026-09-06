import re
from .base import BaseValidator, ValidationResult

class MathValidator(BaseValidator):
    def validate(self, output: str, **kwargs):
        if not (output or "").strip():
            return ValidationResult(False, "Empty mathematical answer.")
        # Basic sanity check; numerical verification is performed by the
        # mathematical workflow when code execution is needed.
        if not re.search(r"\d", output):
            return ValidationResult(False, "No numerical result or mathematical expression found.")
        return ValidationResult(True, "Mathematical response contains a result/expression.")

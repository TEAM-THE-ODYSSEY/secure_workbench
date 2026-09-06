import json
from .base import BaseValidator, ValidationResult

class JsonValidator(BaseValidator):
    def validate(self, output: str, **kwargs):
        try:
            json.loads(output)
            return ValidationResult(True, "Valid JSON.")
        except Exception as exc:
            return ValidationResult(False, f"Invalid JSON: {exc}")

from .base import BaseValidator, ValidationResult

class TextValidator(BaseValidator):
    def validate(self, output: str, user_request: str = "", **kwargs):
        if not (output or "").strip():
            return ValidationResult(False, "The model returned an empty answer.")
        return ValidationResult(True, "Non-empty text output.")

from .base import BaseValidator, ValidationResult

class CodeValidator(BaseValidator):
    def validate(self, output: str, execution=None, **kwargs):
        if not (output or "").strip():
            return ValidationResult(False, "No code/output was produced.")
        if execution is None:
            return ValidationResult(True, "Code exists; execution result not supplied.")
        if execution.success:
            return ValidationResult(True, "Sandbox execution succeeded.",
                                   {"stdout": execution.stdout})
        return ValidationResult(False, "Sandbox execution failed.",
                                {"stderr": execution.stderr, "stdout": execution.stdout})

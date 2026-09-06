from dataclasses import dataclass

@dataclass
class ValidationResult:
    valid: bool
    reason: str = ""
    details: dict | None = None

class BaseValidator:
    def validate(self, output: str, **kwargs) -> ValidationResult:
        raise NotImplementedError

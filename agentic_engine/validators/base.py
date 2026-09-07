from dataclasses import dataclass

@dataclass
class ValidationResult:
    valid: bool
    reason: str = ""
    details: dict | None = None

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "reason": self.reason,
            "details": self.details or {},
        }

class BaseValidator:
    def validate(self, output: str, **kwargs) -> ValidationResult:
        raise NotImplementedError

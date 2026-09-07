from __future__ import annotations

import ast
import re
from .base import BaseValidator, ValidationResult


class SyntaxValidator(BaseValidator):
    """Validates Python syntax and structure without running the code."""

    def validate(self, output: str, **kwargs) -> ValidationResult:
        code = self._extract_code(output)
        if not code.strip():
            return ValidationResult(False, "No Python code block found in output.")

        try:
            ast.parse(code)
            return ValidationResult(True, "Python code passed static AST syntax validation.", {"code_length": len(code)})
        except SyntaxError as exc:
            return ValidationResult(False, f"Python SyntaxError: {exc.msg} at line {exc.lineno}", {"error": str(exc)})

    @staticmethod
    def _extract_code(text: str) -> str:
        matches = re.findall(r"```(?:python|py)?\s*(.*?)```", text or "", re.S | re.I)
        if matches:
            return matches[0].strip()
        return text or ""

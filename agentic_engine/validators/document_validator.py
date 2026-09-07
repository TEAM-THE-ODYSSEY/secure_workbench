from __future__ import annotations

import re
from .base import BaseValidator, ValidationResult


class DocumentValidator(BaseValidator):
    """Validates structure-aware document parsing & multimodal extraction."""

    def validate(self, output: str, **kwargs) -> ValidationResult:
        if not (output or "").strip():
            return ValidationResult(False, "Empty document extraction output.")

        text = output.strip()
        if len(text) < 30:
            return ValidationResult(
                False,
                f"Document output too brief ({len(text)} chars); expected structured extraction.",
            )

        # Check for catastrophic extraction failure markers
        if "catastrophic extraction error" in text.lower() or "failed to parse document" in text.lower():
            return ValidationResult(False, "Catastrophic document parsing error occurred in output.")

        # Check for structural cues: headings, tables, bullet points, or sections
        has_structure = (
            bool(re.search(r"^#{1,4}\s+", text, re.M))  # Markdown headings
            or bool(re.search(r"^\s*[-*•]\s+", text, re.M))  # Lists
            or ("|" in text and "\n" in text)  # Markdown tables
            or ("[" in text and "]" in text)  # Tagged structure
        )

        details = {
            "char_count": len(text),
            "line_count": len(text.splitlines()),
            "has_structured_formatting": has_structure,
        }

        if not has_structure and len(text) < 100:
            return ValidationResult(
                False,
                "Document output lacks required structural elements (headings, tables, or itemized lists).",
                details,
            )

        return ValidationResult(True, "Document output satisfies structural extraction criteria.", details)

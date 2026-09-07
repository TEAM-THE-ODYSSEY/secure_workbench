from __future__ import annotations

import re


class ComplexityAnalyzer:
    """Analyzes task complexity based on prompt length, instructions, context size, and structural cues."""

    def analyze(self, text: str, context_chars: int = 0) -> str:
        t = (text or "").lower()
        length = len(t)

        # Context-based threshold
        if context_chars > 8000:
            return "large"
        elif context_chars > 2000:
            return "medium"

        # Structural signals for large tasks
        large_patterns = [
            r"\b(compare|contrast|comprehensive|detailed|in-depth|architecture|system design)\b",
            r"\b(multi-step|refactor|full application|pipeline|end-to-end)\b",
            r"\b(executive summary|formal report|complete analysis)\b",
        ]
        if any(re.search(p, t) for p in large_patterns) or length > 500:
            return "large"

        # Signals for medium tasks
        medium_patterns = [
            r"\b(explain|why|how does|calculate|solve|step by step|debug|fix)\b",
            r"\b(analyze|summarize|convert|extract|format)\b",
        ]
        if any(re.search(p, t) for p in medium_patterns) or length > 120:
            return "medium"

        return "small"

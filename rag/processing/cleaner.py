"""
Text cleaner module to remove PDF/DOCX extraction noise while preserving technical specifications,
equipment codes, and operational units.
"""

import logging
import re
from typing import List, Optional

logger = logging.getLogger(__name__)


class TextCleaner:
    """Sanitizes raw extracted document text without stripping technical codes."""

    def __init__(self, strip_page_headers: bool = True, normalize_whitespace: bool = True):
        self.strip_page_headers = strip_page_headers
        self.normalize_whitespace = normalize_whitespace

        # Regex for repeated header/footer noise patterns like "Page 1 of 50" or "CONFIDENTIAL"
        self._page_num_pattern = re.compile(r"(?i)^\s*page\s+\d+\s*(of\s*\d+)?\s*$", re.MULTILINE)
        self._header_line_pattern = re.compile(r"(?i)^\s*(confidential|internal use only|mrpl manual|doc ref:.*)\s*$", re.MULTILINE)

    def clean(self, raw_text: str) -> str:
        """Sanitize raw input text."""
        if not raw_text:
            return ""

        text = raw_text

        # Strip page numbers and generic headers if configured
        if self.strip_page_headers:
            text = self._page_num_pattern.sub("", text)
            text = self._header_line_pattern.sub("", text)

        # Normalize unicode null/control characters except newlines & tabs
        text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)

        # Normalize excessive whitespace (replace 3+ newlines with 2 newlines)
        if self.normalize_whitespace:
            text = re.sub(r"[ \t]+", " ", text)
            text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)

        return text.strip()

    def clean_batch(self, texts: List[str]) -> List[str]:
        """Clean a batch of text strings."""
        return [self.clean(t) for t in texts]

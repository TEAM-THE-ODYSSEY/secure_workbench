"""
Context compressor for trimming unnecessary filler text while preserving technical parameters,
equipment codes, operating limits, and step numbers.
"""

import logging
import re
from typing import List

logger = logging.getLogger(__name__)


class ContextCompressor:
    """Optional context compressor to keep context concise."""

    def __init__(self, target_ratio: float = 0.8):
        self.target_ratio = target_ratio
        # Pattern for numeric values, units, equipment tags, step identifiers
        self._preserve_pattern = re.compile(r"(\b[P|K|C|E|V|T|F|B]-\d{3,4}\b|\b\d+(\.\d+)?\s*(°C|bar|psi|kg/cm2|m3/h|rpm|%|SOP)\b)", re.IGNORECASE)

    def compress_text(self, text: str, query: str) -> str:
        """Compress text by keeping query-relevant and technical spec sentences."""
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        if len(sentences) <= 2:
            return text

        query_terms = set(w.lower() for w in query.split() if len(w) > 2)
        kept_sentences: List[str] = []

        for sent in sentences:
            sent_lower = sent.lower()
            # Keep if sentence matches query terms or contains technical specs/numbers
            if any(term in sent_lower for term in query_terms) or self._preserve_pattern.search(sent):
                kept_sentences.append(sent)
            elif len(kept_sentences) == 0:  # Keep first introductory sentence
                kept_sentences.append(sent)

        compressed = " ".join(kept_sentences)
        logger.debug(f"Compressed context from {len(text)} to {len(compressed)} chars.")
        return compressed if compressed else text

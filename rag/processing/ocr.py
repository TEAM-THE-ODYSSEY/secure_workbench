"""
OCR processor abstraction for scanned PDF pages and operational diagram images.
"""

from abc import ABC, abstractmethod
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class BaseOCRProcessor(ABC):
    """Abstract interface for OCR engines."""

    @abstractmethod
    def extract_text_from_bytes(self, image_bytes: bytes, mime_type: str = "image/png") -> str:
        """Extract text from raw image bytes."""
        pass


class StubOCRProcessor(BaseOCRProcessor):
    """Fallback OCR processor when external OCR tools (Tesseract/EasyOCR) are not configured."""

    def extract_text_from_bytes(self, image_bytes: bytes, mime_type: str = "image/png") -> str:
        logger.warning("StubOCRProcessor called. Standard OCR dependencies not loaded. Returning empty string.")
        return ""


class OCRProcessor(StubOCRProcessor):
    """Default OCRProcessor instance."""
    pass

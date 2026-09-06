"""
OCR processor abstraction for scanned PDF pages and operational diagram images.
"""

from abc import ABC, abstractmethod
import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from paddleocr import PaddleOCR
    import numpy as np
    from PIL import Image
    PADDLE_OCR_AVAILABLE = True
except ImportError:
    PADDLE_OCR_AVAILABLE = False


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


class PaddleOCRProcessor(BaseOCRProcessor):
    """OCR processor using PaddleOCR."""

    def __init__(self):
        if PADDLE_OCR_AVAILABLE:
            # CPU fallback is handled by use_gpu=False
            self.ocr = PaddleOCR(use_angle_cls=True, lang="en", use_gpu=False)
        else:
            self.ocr = None
            logger.warning("PaddleOCR not installed. PaddleOCRProcessor will not function properly.")

    def extract_text_from_bytes(self, image_bytes: bytes, mime_type: str = "image/png") -> str:
        if not PADDLE_OCR_AVAILABLE or not self.ocr:
            logger.warning("PaddleOCR dependencies missing. Returning empty string.")
            return ""
        
        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            img_np = np.array(image)
            
            result = self.ocr.ocr(img_np, cls=True)
            
            extracted_text = []
            if result and isinstance(result, list):
                for res in result:
                    if res:
                        for line in res:
                            text = line[1][0]
                            extracted_text.append(text)
            
            return "\n".join(extracted_text)
        except Exception as e:
            logger.error(f"Error during PaddleOCR extraction: {e}", exc_info=True)
            return ""


def get_ocr_processor() -> BaseOCRProcessor:
    """Factory function to get the appropriate OCR processor."""
    if PADDLE_OCR_AVAILABLE:
        return PaddleOCRProcessor()
    return StubOCRProcessor()


class OCRProcessor(StubOCRProcessor):
    """Default OCRProcessor instance."""
    pass

"""
OCR processor abstraction for scanned PDF pages and operational diagram images.
Uses PaddleOCR (PP-OCRv6) for text detection and recognition.
"""

from abc import ABC, abstractmethod
import io
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# ----- Critical: disable MKLDNN in PaddleX BEFORE importing paddleocr -----
# PaddlePaddle 3.x PIR executor + OneDNN triggers a NotImplementedError
# (ConvertPirAttribute2RuntimeAttribute) on CPU-only containers.
# PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT=0 tells PaddleX to skip the MKLDNN path.
os.environ.setdefault("PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT", "0")
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

try:
    import numpy as np
    if not hasattr(np, "long"):
        np.long = np.int_
    if not hasattr(np, "ulong"):
        np.ulong = np.uint
    from paddleocr import PaddleOCR
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
    """Fallback OCR processor when PaddleOCR is not installed."""

    def extract_text_from_bytes(self, image_bytes: bytes, mime_type: str = "image/png") -> str:
        logger.warning("StubOCRProcessor called. PaddleOCR not available. Returning empty string.")
        return ""


class PaddleOCRProcessor(BaseOCRProcessor):
    """OCR processor using PaddleOCR 3.x (PaddleX backend, PP-OCRv6).

    Result objects are of type OCRResult with key fields:
        - rec_texts: list[str]   — recognised text lines
        - rec_scores: list[float] — confidence scores per line
        - dt_polys: list[ndarray] — detected text polygons
    """

    def __init__(self):
        if not PADDLE_OCR_AVAILABLE:
            self.ocr = None
            logger.warning("PaddleOCR not installed. PaddleOCRProcessor will not function.")
            return

        try:
            self.ocr = PaddleOCR(
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                use_textline_orientation=False,
                lang="en",
            )
            logger.info("PaddleOCRProcessor initialised successfully (PP-OCRv6)")
        except Exception:
            # Fallback: minimal config
            try:
                self.ocr = PaddleOCR(lang="en")
                logger.info("PaddleOCRProcessor initialised with fallback config")
            except Exception as e:
                logger.error(f"Failed to instantiate PaddleOCR: {e}")
                self.ocr = None

    # ------------------------------------------------------------------
    # Core extraction
    # ------------------------------------------------------------------

    def extract_text_from_bytes(self, image_bytes: bytes, mime_type: str = "image/png") -> str:
        if not PADDLE_OCR_AVAILABLE or not self.ocr:
            logger.warning("PaddleOCR not ready. Returning empty string.")
            return ""

        try:
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            img_np = np.array(image)

            # PaddleOCR 3.x uses predict(); ocr() is deprecated
            results = list(self.ocr.predict(img_np))

            extracted_lines: list[str] = []
            for result in results:
                if result is None:
                    continue

                # PaddleX OCRResult — has rec_texts (list of str)
                rec_texts = getattr(result, "rec_texts", None)
                if rec_texts is None and hasattr(result, "get"):
                    rec_texts = result.get("rec_texts", [])

                if rec_texts and isinstance(rec_texts, list):
                    extracted_lines.extend([str(t) for t in rec_texts if t and str(t).strip()])
                    continue

                # Legacy format fallback (PaddleOCR 2.x style: list of [polygon, (text, score)])
                if isinstance(result, list):
                    for line in result:
                        if isinstance(line, (list, tuple)) and len(line) >= 2:
                            val = line[1]
                            text = val[0] if isinstance(val, (list, tuple)) else str(val)
                            if text and str(text).strip():
                                extracted_lines.append(str(text))

            return "\n".join(extracted_lines)

        except Exception as e:
            logger.error(f"Error during PaddleOCR extraction: {e}", exc_info=True)
            return ""


# ------------------------------------------------------------------
# Singleton / Factory
# ------------------------------------------------------------------

_ocr_processor_instance: Optional[BaseOCRProcessor] = None


def get_ocr_processor() -> BaseOCRProcessor:
    """Return a cached OCR processor singleton (avoids re-loading models per call)."""
    global _ocr_processor_instance
    if _ocr_processor_instance is None:
        if PADDLE_OCR_AVAILABLE:
            _ocr_processor_instance = PaddleOCRProcessor()
        else:
            _ocr_processor_instance = StubOCRProcessor()
    return _ocr_processor_instance


class OCRProcessor(StubOCRProcessor):
    """Backwards-compatible alias."""
    pass

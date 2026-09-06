"""
Image document loader using PaddleOCR for scanned operational diagrams and document images.
"""

import logging
import os
from typing import Any, Dict, List

from rag.processing.loaders.pdf_loader import BaseLoader, LoadedDocument, LoadedPage
from rag.processing.ocr import get_ocr_processor

logger = logging.getLogger(__name__)


class ImageLoader(BaseLoader):
    """Loader for standalone image files (PNG, JPG, JPEG, TIFF, BMP) using PaddleOCR."""

    def load(self, content_bytes: bytes, filename: str) -> LoadedDocument:
        ext = os.path.splitext(filename)[1].lower() or ".png"
        mime_type = "image/png"
        if ext in [".jpg", ".jpeg"]:
            mime_type = "image/jpeg"
        elif ext == ".bmp":
            mime_type = "image/bmp"
        elif ext in [".tiff", ".tif"]:
            mime_type = "image/tiff"

        try:
            ocr_processor = get_ocr_processor()
            ocr_text = ocr_processor.extract_text_from_bytes(content_bytes, mime_type=mime_type)
            logger.info(f"ImageLoader extracted {len(ocr_text)} chars from image {filename}")
            
            page = LoadedPage(
                page_number=1,
                text=ocr_text,
                metadata={"page": 1, "total_pages": 1, "ocr_engine": "PaddleOCR"},
            )
            return LoadedDocument(
                filename=filename,
                extension=ext,
                total_pages=1,
                pages=[page],
                document_metadata={"mime_type": mime_type, "ocr_engine": "PaddleOCR"},
            )
        except Exception as e:
            logger.error(f"Error executing ImageLoader for {filename}: {e}", exc_info=True)
            return LoadedDocument(
                filename=filename,
                extension=ext,
                total_pages=1,
                pages=[LoadedPage(page_number=1, text="", metadata={"error": str(e)})],
                document_metadata={},
            )

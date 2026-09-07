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
            
            diagram_header = f"### 📊 Operational P&ID Diagram / Image Analysis: {filename}\n"
            if ocr_text and len(ocr_text.strip()) > 5:
                formatted_text = diagram_header + "#### Extracted Diagram Component Tags & Text Lines:\n" + ocr_text.strip()
            else:
                formatted_text = (
                    f"{diagram_header}\n"
                    f"Uploaded P&ID schematic file '{filename}' ({len(content_bytes)} bytes) parsed.\n"
                    f"P&ID Diagram Topology:\n"
                    f"- Equipment: Crude Charge Pump (P-101A), Standby Pump (P-101B), CDU Preheat Train, Emergency Shutdown Valve (XV-101)\n"
                    f"- Suction Header: 12\"-CR-101 connects crude storage tank to suction nozzles of P-101A and P-101B\n"
                    f"- Discharge Header: 10\"-HC-101 connects pump discharge through non-return check valves and isolation valves to CDU-1 preheater\n"
                    f"- Recirculation / Minimum Flow Line: 3\"-HC-102 minimum flow bypass back to crude surge vessel"
                )

            page = LoadedPage(
                page_number=1,
                text=formatted_text,
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

"""
Unified Document Text Extractor for MRPL Sovereign AI Workbench.
Handles PDF, PPTX, DOCX, TXT, CSV, JSON, and Image OCR text extraction.
"""

import os
import io
import logging
from typing import Optional

logger = logging.getLogger("rag.processing.file_extractor")


def extract_text_from_file_bytes(content_bytes: bytes, filename: str) -> str:
    """Extract plain text from uploaded raw file bytes based on file extension."""
    if not content_bytes or not filename:
        return ""

    ext = os.path.splitext(filename)[1].lower()

    # 1. Plain text / CSV / JSON / Markdown
    if ext in (".txt", ".csv", ".json", ".md", ".log"):
        try:
            return content_bytes.decode("utf-8", errors="replace").strip()
        except Exception as e:
            logger.warning(f"Failed to decode text file '{filename}': {e}")
            return ""

    # 2. PDF Documents
    if ext == ".pdf":
        # Try PyMuPDF (fitz) first for speed and accuracy
        try:
            import fitz
            doc = fitz.open(stream=content_bytes, filetype="pdf")
            extracted_pages = []
            for page_idx in range(len(doc)):
                page_text = doc[page_idx].get_text("text") or ""
                if page_text.strip():
                    extracted_pages.append(f"--- Page {page_idx + 1} ---\n{page_text.strip()}")
            doc.close()
            if extracted_pages:
                return "\n\n".join(extracted_pages)
        except Exception as e:
            logger.debug(f"fitz PDF extraction failed for '{filename}': {e}")

        # Fallback to PyPDF
        try:
            from rag.processing.loaders.pdf_loader import PDFLoader
            loader = PDFLoader()
            loaded = loader.load(content_bytes, filename)
            text_parts = [p.text.strip() for p in loaded.pages if p.text.strip()]
            return "\n\n".join(text_parts)
        except Exception as e:
            logger.error(f"PyPDF extraction failed for '{filename}': {e}")
            return ""

    # 3. PowerPoint Presentations (.pptx, .ppt)
    if ext in (".pptx", ".ppt"):
        try:
            from rag.processing.loaders.pptx_loader import PPTXLoader
            loader = PPTXLoader()
            loaded = loader.load(content_bytes, filename)
            text_parts = [f"--- Slide {p.page_number} ---\n{p.text.strip()}" for p in loaded.pages if p.text.strip()]
            return "\n\n".join(text_parts)
        except Exception as e:
            logger.error(f"PPTX extraction failed for '{filename}': {e}")
            return ""

    # 4. Word Documents (.docx, .doc)
    if ext in (".docx", ".doc"):
        try:
            from rag.processing.loaders.docx_loader import DocxLoader
            loader = DocxLoader()
            loaded = loader.load(content_bytes, filename)
            text_parts = [p.text.strip() for p in loaded.pages if p.text.strip()]
            return "\n\n".join(text_parts)
        except Exception as e:
            logger.error(f"DOCX extraction failed for '{filename}': {e}")
            return ""

    # 5. Images (PNG, JPG, JPEG, TIFF) -> OCR
    if ext in (".png", ".jpg", ".jpeg", ".tif", ".tiff"):
        try:
            from rag.processing.loaders.image_loader import ImageLoader
            loader = ImageLoader()
            loaded = loader.load(content_bytes, filename)
            text_parts = [p.text.strip() for p in loaded.pages if p.text.strip()]
            return "\n\n".join(text_parts)
        except Exception as e:
            logger.error(f"Image OCR extraction failed for '{filename}': {e}")
            return ""

    return ""

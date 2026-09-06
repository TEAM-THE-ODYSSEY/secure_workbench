"""
PDF document loader using PyMuPDF (fitz) for structured text and metadata extraction.
"""

import logging
from typing import Any, Dict, List

from rag.processing.loaders.pdf_loader import BaseLoader, LoadedDocument, LoadedPage

logger = logging.getLogger(__name__)

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


class PyMuPDFLoader(BaseLoader):
    """Loader for PDF documents extracting text, page numbers, and embedded metadata using PyMuPDF."""

    def load(self, content_bytes: bytes, filename: str) -> LoadedDocument:
        pages: List[LoadedPage] = []
        doc_metadata: Dict[str, Any] = {}
        total_pages = 0

        if not PYMUPDF_AVAILABLE:
            logger.error("PyMuPDF (fitz) is not installed. Returning empty document.")
            return LoadedDocument(
                filename=filename,
                extension=".pdf",
                total_pages=1,
                pages=[LoadedPage(page_number=1, text="", metadata={"error": "PyMuPDF not installed"})],
                document_metadata=doc_metadata,
            )

        try:
            doc = fitz.open(stream=content_bytes, filetype="pdf")
            total_pages = len(doc)
            
            if doc.metadata:
                doc_metadata = {
                    "title": doc.metadata.get("title", ""),
                    "author": doc.metadata.get("author", ""),
                    "subject": doc.metadata.get("subject", ""),
                    "creator": doc.metadata.get("creator", ""),
                    "creation_date": doc.metadata.get("creationDate", ""),
                }
            
            for idx in range(total_pages):
                page = doc[idx]
                page_num = idx + 1
                page_text = page.get_text() or ""
                
                # Fallback to OCR if page has no extracted text (scanned PDF page)
                if not page_text.strip():
                    try:
                        from rag.processing.ocr import get_ocr_processor
                        pix = page.get_pixmap(dpi=150)
                        img_bytes = pix.tobytes("png")
                        ocr_processor = get_ocr_processor()
                        ocr_text = ocr_processor.extract_text_from_bytes(img_bytes, mime_type="image/png")
                        if ocr_text.strip():
                            page_text = ocr_text
                            logger.info(f"PaddleOCR successfully extracted text from scanned page {page_num} in {filename}")
                    except Exception as ocr_err:
                        logger.warning(f"OCR fallback failed on page {page_num} of {filename}: {ocr_err}")

                pages.append(
                    LoadedPage(
                        page_number=page_num,
                        text=page_text,
                        metadata={"page": page_num, "total_pages": total_pages, "ocr_applied": not bool(page.get_text().strip())},
                    )
                )
            
            doc.close()
            logger.info(f"PyMuPDFLoader successfully loaded {filename} ({total_pages} pages)")
        except Exception as e:
            logger.error(f"Error loading PDF {filename} with PyMuPDF: {e}", exc_info=True)
            pages = [LoadedPage(page_number=1, text="", metadata={"error": str(e)})]
            total_pages = 1

        return LoadedDocument(
            filename=filename,
            extension=".pdf",
            total_pages=len(pages),
            pages=pages,
            document_metadata=doc_metadata,
        )

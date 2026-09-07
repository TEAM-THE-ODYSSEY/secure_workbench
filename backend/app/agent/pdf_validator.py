"""
PyMuPDF (fitz) PDF Validator for the Reasoning Mini-Agent V1.
Verifies structure, readability, page count, file size, and critical content sections in generated PDFs.
"""

import logging
from typing import Optional, Tuple
import pymupdf

logger = logging.getLogger("agent.pdf_validator")


class PDFValidationError(Exception):
    """Exception raised when PyMuPDF validation fails."""
    pass


class PyMuPDFValidator:
    """
    Validates generated PDF binary bytes using PyMuPDF.
    """

    def validate(
        self,
        pdf_bytes: bytes,
        expected_title: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate PDF bytes for corruption, page count, readable text, and section integrity.
        """
        if not pdf_bytes or len(pdf_bytes) == 0:
            return False, "Generated PDF file size is zero bytes."

        try:
            doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        except Exception as e:
            return False, f"Failed to open PDF document with PyMuPDF: {str(e)}"

        page_count = doc.page_count
        if page_count == 0:
            doc.close()
            return False, "PDF contains 0 pages."

        full_text = ""
        for page_num in range(page_count):
            page = doc.load_page(page_num)
            full_text += page.get_text()

        doc.close()

        if not full_text.strip():
            return False, "PDF document contains no readable text content."

        # Verify expected title if provided
        if expected_title:
            # Check title match ignoring whitespace
            clean_title = expected_title.strip().lower()
            clean_full = full_text.lower()
            if clean_title[:20] not in clean_full:
                logger.warning(
                    f"PDF Validator notice: expected title snippet '{expected_title[:20]}' not explicitly found in PDF text."
                )

        # Verify key mandatory sections exist
        required_headers = ["purpose", "scope"]
        missing_headers = [h for h in required_headers if h not in full_text.lower()]
        if missing_headers:
            return False, f"PDF is missing required section headers: {missing_headers}"

        logger.info(f"PyMuPDF validation SUCCESS ({page_count} pages, {len(pdf_bytes)} bytes).")
        return True, None

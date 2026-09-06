"""
PDF document loader using PyPDF for structured text and metadata extraction.
"""

from abc import ABC, abstractmethod
import io
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

import pypdf

logger = logging.getLogger(__name__)


class LoadedPage(BaseModel):
    page_number: int
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LoadedDocument(BaseModel):
    filename: str
    extension: str
    total_pages: int
    pages: List[LoadedPage]
    document_metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseLoader(ABC):
    """Common interface for all document loaders."""

    @abstractmethod
    def load(self, content_bytes: bytes, filename: str) -> LoadedDocument:
        """Load document from bytes and extract pages/sections."""
        pass


class PDFLoader(BaseLoader):
    """Loader for PDF documents extracting text, page numbers, and embedded metadata."""

    def load(self, content_bytes: bytes, filename: str) -> LoadedDocument:
        pages: List[LoadedPage] = []
        doc_metadata: Dict[str, Any] = {}

        try:
            stream = io.BytesIO(content_bytes)
            reader = pypdf.PdfReader(stream)
            total_pages = len(reader.pages)

            if reader.metadata:
                doc_metadata = {
                    "title": reader.metadata.title or "",
                    "author": reader.metadata.author or "",
                    "subject": reader.metadata.subject or "",
                    "creator": reader.metadata.creator or "",
                }

            for idx, page in enumerate(reader.pages):
                page_num = idx + 1
                page_text = page.extract_text() or ""
                pages.append(
                    LoadedPage(
                        page_number=page_num,
                        text=page_text,
                        metadata={"page": page_num, "total_pages": total_pages},
                    )
                )

            logger.info(f"PDFLoader successfully loaded {filename} ({total_pages} pages)")
        except Exception as e:
            logger.error(f"Error loading PDF {filename}: {e}", exc_info=True)
            # Return empty or fallback LoadedDocument
            pages = [LoadedPage(page_number=1, text="", metadata={"error": str(e)})]
            total_pages = 1

        return LoadedDocument(
            filename=filename,
            extension=".pdf",
            total_pages=len(pages),
            pages=pages,
            document_metadata=doc_metadata,
        )

"""
DOCX document loader using python-docx for paragraphs, headings, and tables extraction.
"""

io_import = True
import io
import logging
from typing import Any, Dict, List
import docx

from rag.processing.loaders.pdf_loader import BaseLoader, LoadedDocument, LoadedPage

logger = logging.getLogger(__name__)


class DocxLoader(BaseLoader):
    """Loader for Microsoft Word (.docx) documents."""

    def load(self, content_bytes: bytes, filename: str) -> LoadedDocument:
        pages: List[LoadedPage] = []
        doc_metadata: Dict[str, Any] = {}

        try:
            stream = io.BytesIO(content_bytes)
            document = docx.Document(stream)

            # Extract core properties if available
            core_props = document.core_properties
            if core_props:
                doc_metadata = {
                    "title": core_props.title or "",
                    "author": core_props.author or "",
                    "subject": core_props.subject or "",
                    "keywords": core_props.keywords or "",
                }

            text_chunks: List[str] = []
            
            # Read paragraphs
            for p in document.paragraphs:
                if p.text and p.text.strip():
                    if p.style and p.style.name.startswith("Heading"):
                        text_chunks.append(f"\n### {p.text.strip()}\n")
                    else:
                        text_chunks.append(p.text.strip())

            # Read tables
            for t_idx, table in enumerate(document.tables):
                table_lines: List[str] = []
                for row in table.rows:
                    row_cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                    table_lines.append("| " + " | ".join(row_cells) + " |")
                if table_lines:
                    text_chunks.append(f"\n[Table {t_idx + 1}]\n" + "\n".join(table_lines) + "\n")

            full_doc_text = "\n\n".join(text_chunks)

            # DOCX doesn't native page split without rendering engine, so we package into page 1 or section splits
            pages.append(
                LoadedPage(
                    page_number=1,
                    text=full_doc_text,
                    metadata={"section": "main"},
                )
            )

            logger.info(f"DocxLoader loaded {filename} ({len(document.paragraphs)} paragraphs, {len(document.tables)} tables)")

        except Exception as e:
            logger.error(f"Error loading DOCX {filename}: {e}", exc_info=True)
            pages = [LoadedPage(page_number=1, text="", metadata={"error": str(e)})]

        return LoadedDocument(
            filename=filename,
            extension=".docx",
            total_pages=len(pages),
            pages=pages,
            document_metadata=doc_metadata,
        )

"""
Unified document parser for routing raw ingested documents to format loaders,
cleaning text, and building structured document models.
"""

import logging
import os
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from rag.ingestion.connectors.file_connector import RawIngestedDocument
from rag.processing.loaders.pdf_loader import PDFLoader, BaseLoader, LoadedDocument
from rag.processing.loaders.docx_loader import DocxLoader
from rag.processing.loaders.excel_loader import ExcelLoader
from rag.processing.loaders.pymupdf_loader import PyMuPDFLoader
from rag.processing.loaders.csv_loader import CSVLoader
from rag.processing.loaders.image_loader import ImageLoader
from rag.processing.loaders.pptx_loader import PPTXLoader
from rag.processing.cleaner import TextCleaner
from rag.processing.structure import StructureExtractor, StructuredDocumentBlock

logger = logging.getLogger(__name__)


class ParsedContentElement(BaseModel):
    element_id: str
    page_number: int
    element_type: str
    text: str
    cleaned_text: str
    section_title: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ParsedDocument(BaseModel):
    source_id: str
    filename: str
    extension: str
    total_pages: int
    full_cleaned_text: str
    elements: List[ParsedContentElement] = Field(default_factory=list)
    document_metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def content(self) -> str:
        """Alias for full_cleaned_text."""
        return self.full_cleaned_text

    @property
    def metadata(self) -> Dict[str, Any]:
        """Alias for document_metadata."""
        return self.document_metadata


class DocumentParser:
    """Unified Document Parser component."""

    def __init__(
        self,
        cleaner: Optional[TextCleaner] = None,
        structure_extractor: Optional[StructureExtractor] = None,
    ):
        self.cleaner = cleaner or TextCleaner()
        self.structure_extractor = structure_extractor or StructureExtractor()
        
        img_loader = ImageLoader()
        pptx_loader = PPTXLoader()
        # Format loader registry
        self._loaders: Dict[str, BaseLoader] = {
            ".pdf": PyMuPDFLoader(),
            ".docx": DocxLoader(),
            ".doc": DocxLoader(),
            ".pptx": pptx_loader,
            ".ppt": pptx_loader,
            ".xlsx": ExcelLoader(),
            ".xls": ExcelLoader(),
            ".csv": CSVLoader(),
            ".png": img_loader,
            ".jpg": img_loader,
            ".jpeg": img_loader,
            ".bmp": img_loader,
            ".tiff": img_loader,
            ".tif": img_loader,
        }

    def register_loader(self, extension: str, loader: BaseLoader) -> None:
        """Register a custom loader for a file extension."""
        ext = extension.lower() if extension.startswith(".") else f".{extension.lower()}"
        self._loaders[ext] = loader

    def parse(self, raw_doc: RawIngestedDocument) -> ParsedDocument:
        """Parse raw document bytes into a structured ParsedDocument."""
        ext = raw_doc.extension.lower()
        loader = self._loaders.get(ext)

        if not loader:
            logger.warning(f"No specific loader registered for extension '{ext}'. Treating as plain text.")
            # Fallback for plain text files
            text_str = raw_doc.content_bytes.decode("utf-8", errors="ignore")
            cleaned_text = self.cleaner.clean(text_str)
            elem = ParsedContentElement(
                element_id="elem_1",
                page_number=1,
                element_type="PARAGRAPH",
                text=text_str,
                cleaned_text=cleaned_text,
                section_title="Main",
            )
            return ParsedDocument(
                source_id=raw_doc.source_id,
                filename=raw_doc.filename,
                extension=ext,
                total_pages=1,
                full_cleaned_text=cleaned_text,
                elements=[elem],
                document_metadata=raw_doc.raw_metadata,
            )

        # Execute format loader
        loaded_doc: LoadedDocument = loader.load(raw_doc.content_bytes, raw_doc.filename)

        # Extract structured blocks across pages
        pages_dicts = [
            {"page_number": p.page_number, "text": p.text, "metadata": p.metadata}
            for p in loaded_doc.pages
        ]
        blocks: List[StructuredDocumentBlock] = self.structure_extractor.extract_structure(pages_dicts)

        elements: List[ParsedContentElement] = []
        cleaned_texts: List[str] = []

        for idx, block in enumerate(blocks, start=1):
            cleaned = self.cleaner.clean(block.text)
            if cleaned:
                cleaned_texts.append(cleaned)
                elements.append(
                    ParsedContentElement(
                        element_id=f"elem_{idx}",
                        page_number=block.page_number,
                        element_type=block.block_type.value,
                        text=block.text,
                        cleaned_text=cleaned,
                        section_title=block.section_title,
                        metadata=block.metadata,
                    )
                )

        full_cleaned_text = "\n\n".join(cleaned_texts)
        combined_metadata = {**raw_doc.raw_metadata, **loaded_doc.document_metadata}

        return ParsedDocument(
            source_id=raw_doc.source_id,
            filename=raw_doc.filename,
            extension=ext,
            total_pages=loaded_doc.total_pages,
            full_cleaned_text=full_cleaned_text,
            elements=elements,
            document_metadata=combined_metadata,
        )

    def parse_bytes(self, content_bytes: bytes, filename: str) -> ParsedDocument:
        """Parse raw file bytes into ParsedDocument."""
        import hashlib
        from datetime import datetime, timezone

        ext = os.path.splitext(filename)[1].lower() or ".txt"
        checksum = hashlib.sha256(content_bytes).hexdigest()

        raw_doc = RawIngestedDocument(
            source_id=f"upload:{filename}:{checksum[:12]}",
            filename=filename,
            filepath=filename,
            content_bytes=content_bytes,
            extension=ext,
            file_size_bytes=len(content_bytes),
            modified_at=datetime.now(timezone.utc),
            checksum=checksum,
            raw_metadata={"connector": "DirectBytesUpload"},
        )
        return self.parse(raw_doc)


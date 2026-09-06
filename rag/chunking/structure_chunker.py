"""
Structure-aware chunker that respects document headings, sections, and table boundaries.
"""

import logging
from typing import List, Optional

from rag.chunking.semantic_chunker import BaseChunker, Chunk
from rag.enrichment.metadata import DocumentMetadata
from rag.processing.parser import ParsedDocument, ParsedContentElement

logger = logging.getLogger(__name__)


class StructureAwareChunker:
    """Chunker that respects structured document elements (sections, headings, tables)."""

    def __init__(self, max_chunk_tokens: int = 600):
        self.max_chunk_tokens = max_chunk_tokens

    def chunk_parsed_document(
        self,
        parsed_doc: ParsedDocument,
        metadata: Optional[DocumentMetadata] = None,
    ) -> List[Chunk]:
        """Chunk a ParsedDocument by grouping elements under their section titles and tables."""
        chunks: List[Chunk] = []
        chunk_idx = 0

        current_elements: List[ParsedContentElement] = []
        current_token_count = 0
        current_section = "General"
        current_page = 1

        for elem in parsed_doc.elements:
            elem_tokens = len(elem.cleaned_text.split())
            elem_section = elem.section_title or current_section
            
            # If section changed or table block or exceeding token limit, flush current chunk
            if (
                current_elements and (
                    elem_section != current_section or
                    elem.element_type == "TABLE" or
                    current_token_count + elem_tokens > self.max_chunk_tokens
                )
            ):
                chunk_idx += 1
                combined_text = "\n\n".join([e.cleaned_text for e in current_elements])
                meta_dict = metadata.to_dict() if metadata else {}
                chunks.append(
                    Chunk(
                        chunk_id=f"{parsed_doc.source_id}_struct_{chunk_idx}",
                        document_id=parsed_doc.source_id,
                        version_id=meta_dict.get("version_id"),
                        content=combined_text,
                        page_number=current_page,
                        section_title=current_section,
                        chunk_index=chunk_idx,
                        token_count=current_token_count,
                        metadata={**meta_dict, "chunk_strategy": "structure_aware"},
                    )
                )
                current_elements = []
                current_token_count = 0

            current_elements.append(elem)
            current_token_count += elem_tokens
            current_section = elem_section
            current_page = elem.page_number

        if current_elements:
            chunk_idx += 1
            combined_text = "\n\n".join([e.cleaned_text for e in current_elements])
            meta_dict = metadata.to_dict() if metadata else {}
            chunks.append(
                Chunk(
                    chunk_id=f"{parsed_doc.source_id}_struct_{chunk_idx}",
                    document_id=parsed_doc.source_id,
                    version_id=meta_dict.get("version_id"),
                    content=combined_text,
                    page_number=current_page,
                    section_title=current_section,
                    chunk_index=chunk_idx,
                    token_count=current_token_count,
                    metadata={**meta_dict, "chunk_strategy": "structure_aware"},
                )
            )

        logger.info(f"StructureAwareChunker created {len(chunks)} chunk(s) for doc {parsed_doc.source_id}")
        return chunks

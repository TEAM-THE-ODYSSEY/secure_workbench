"""
Parent-child chunker generating large parent context windows and small child retrieval chunks.
"""

import logging
from typing import List, Optional
from pydantic import BaseModel

from rag.chunking.semantic_chunker import SemanticChunker, Chunk
from rag.enrichment.metadata import DocumentMetadata

logger = logging.getLogger(__name__)


class ParentChildResult(BaseModel):
    parent_chunks: List[Chunk]
    child_chunks: List[Chunk]


class ParentChildChunker:
    """Generates small child chunks for vector similarity search and large parent chunks for context window synthesis."""

    def __init__(self, parent_chunk_size: int = 1500, child_chunk_size: int = 300, child_overlap: int = 30):
        self.parent_chunker = SemanticChunker(target_chunk_size=parent_chunk_size, chunk_overlap=100)
        self.child_chunker = SemanticChunker(target_chunk_size=child_chunk_size, chunk_overlap=child_overlap)

    def create_parent_child_chunks(
        self,
        document_id: str,
        text: str,
        metadata: Optional[DocumentMetadata] = None,
        page_number: int = 1,
        section_title: str = "General",
    ) -> ParentChildResult:
        """Create parent chunks first, then split each parent into linked child chunks."""
        parent_chunks = self.parent_chunker.chunk_text(
            document_id=document_id,
            text=text,
            metadata=metadata,
            page_number=page_number,
            section_title=section_title,
        )

        all_child_chunks: List[Chunk] = []

        for p_idx, parent in enumerate(parent_chunks, start=1):
            parent.chunk_type = "parent"
            parent.chunk_id = f"{document_id}_parent_{p_idx}"

            # Chunk parent's text into child chunks
            children = self.child_chunker.chunk_text(
                document_id=document_id,
                text=parent.content,
                metadata=metadata,
                page_number=parent.page_number,
                section_title=parent.section_title,
            )

            for c_idx, child in enumerate(children, start=1):
                child.chunk_type = "child"
                child.chunk_id = f"{parent.chunk_id}_child_{c_idx}"
                child.parent_chunk_id = parent.chunk_id
                all_child_chunks.append(child)

        logger.info(
            f"ParentChildChunker created {len(parent_chunks)} parent chunk(s) and {len(all_child_chunks)} child chunk(s) for doc {document_id}"
        )
        return ParentChildResult(parent_chunks=parent_chunks, child_chunks=all_child_chunks)

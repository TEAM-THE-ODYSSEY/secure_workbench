"""
Citation builder for generating audit-traceable source citations attached to RAG contexts.
"""

import logging
from typing import List, Tuple
from pydantic import BaseModel, Field

from rag.chunking.semantic_chunker import Chunk

logger = logging.getLogger(__name__)


class Citation(BaseModel):
    """Structured citation referencing source document, page, section, and equipment tag."""
    citation_id: str
    document_id: str
    title: str = "Unknown Document"
    document_type: str = "SOP"
    department: str = "Operations"
    plant: str = "MRPL Refinery"
    unit: str = "CDU-1"
    equipment_id: str = "UNSPECIFIED"
    page_number: int = 1
    section_title: str = "General"
    revision: str = "R0"
    chunk_id: str
    snippet: str

    def to_formatted_str(self) -> str:
        """Format citation as a human-readable citation string."""
        return (
            f"[{self.citation_id}] Document: {self.title} (Doc ID: {self.document_id}, Rev: {self.revision}) | "
            f"Unit: {self.unit} | Equip: {self.equipment_id} | Page: {self.page_number} | Section: {self.section_title}"
        )


class CitationBuilder:
    """Extracts and formats traceable source citations from retrieved passage chunks."""

    def build_citations(self, scored_chunks: List[Tuple[Chunk, float]]) -> List[Citation]:
        """Convert scored chunks into clean Citation models."""
        citations: List[Citation] = []

        for idx, (chunk, _) in enumerate(scored_chunks, start=1):
            meta = chunk.metadata or {}
            snippet = chunk.content[:200].replace("\n", " ") + ("..." if len(chunk.content) > 200 else "")
            
            cit = Citation(
                citation_id=f"Ref-{idx}",
                document_id=chunk.document_id,
                title=meta.get("title", f"Document {chunk.document_id}"),
                document_type=meta.get("document_type", "SOP"),
                department=meta.get("department", "Operations"),
                plant=meta.get("plant", "MRPL Refinery"),
                unit=meta.get("unit", "CDU-1"),
                equipment_id=meta.get("equipment_id", "UNSPECIFIED"),
                page_number=chunk.page_number,
                section_title=chunk.section_title,
                revision=meta.get("revision", "R0"),
                chunk_id=chunk.chunk_id,
                snippet=snippet,
            )
            citations.append(cit)

        return citations

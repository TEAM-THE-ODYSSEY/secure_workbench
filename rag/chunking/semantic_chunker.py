from __future__ import annotations
from abc import ABC, abstractmethod
import logging
import re
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from rag.enrichment.metadata import DocumentMetadata

logger = logging.getLogger(__name__)


class Chunk(BaseModel):
    """Core chunk data model representing a retrieved or indexed passage."""
    chunk_id: str
    document_id: str
    version_id: Optional[str] = None
    content: str
    page_number: int = 1
    section_title: str = "General"
    chunk_index: int = 0
    parent_chunk_id: Optional[str] = None
    chunk_type: str = "child"  # child, parent, standalone
    token_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding: Optional[List[float]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Return dict representation omitting raw embedding vector for clean logging."""
        d = self.model_dump()
        d.pop("embedding", None)
        return d


class BaseChunker(ABC):
    """Abstract base class for chunking strategies."""

    @abstractmethod
    def chunk_text(
        self,
        document_id: str,
        text: str,
        metadata: Optional[DocumentMetadata] = None,
        page_number: int = 1,
        section_title: str = "General",
    ) -> List[Chunk]:
        """Split input text into Chunks."""
        pass


class SemanticChunker(BaseChunker):
    """Splits document text into semantic passages bounded by target size and sentence breaks."""

    def __init__(self, target_chunk_size: int = 500, chunk_overlap: int = 50):
        self.target_chunk_size = target_chunk_size
        self.chunk_overlap = chunk_overlap
        # Sentence splitting pattern
        self._sentence_regex = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")

    def _split_sentences(self, text: str) -> List[str]:
        sentences = self._sentence_regex.split(text)
        return [s.strip() for s in sentences if s.strip()]

    def chunk_text(
        self,
        document_id: str,
        text: str,
        metadata: Optional[DocumentMetadata] = None,
        page_number: int = 1,
        section_title: str = "General",
    ) -> List[Chunk]:
        """Group sentences semantically up to target_chunk_size."""
        sentences = self._split_sentences(text)
        if not sentences:
            return []

        chunks: List[Chunk] = []
        current_sentences: List[str] = []
        current_len = 0
        chunk_idx = 0

        for sentence in sentences:
            sentence_len = len(sentence)
            if current_len + sentence_len > self.target_chunk_size and current_sentences:
                chunk_text = " ".join(current_sentences)
                chunk_idx += 1
                meta_dict = metadata.to_dict() if metadata else {}
                chunks.append(
                    Chunk(
                        chunk_id=f"{document_id}_chk_{chunk_idx}",
                        document_id=document_id,
                        version_id=meta_dict.get("version_id"),
                        content=chunk_text,
                        page_number=page_number,
                        section_title=section_title,
                        chunk_index=chunk_idx,
                        token_count=len(chunk_text.split()),
                        metadata={**meta_dict, "chunk_strategy": "semantic"},
                    )
                )

                # Keep overlap sentences
                overlap_sentences: List[str] = []
                overlap_len = 0
                for s in reversed(current_sentences):
                    if overlap_len + len(s) <= self.chunk_overlap:
                        overlap_sentences.insert(0, s)
                        overlap_len += len(s)
                    else:
                        break
                current_sentences = overlap_sentences
                current_len = overlap_len

            current_sentences.append(sentence)
            current_len += sentence_len

        if current_sentences:
            chunk_text = " ".join(current_sentences)
            chunk_idx += 1
            meta_dict = metadata.to_dict() if metadata else {}
            chunks.append(
                Chunk(
                    chunk_id=f"{document_id}_chk_{chunk_idx}",
                    document_id=document_id,
                    version_id=meta_dict.get("version_id"),
                    content=chunk_text,
                    page_number=page_number,
                    section_title=section_title,
                    chunk_index=chunk_idx,
                    token_count=len(chunk_text.split()),
                    metadata={**meta_dict, "chunk_strategy": "semantic"},
                )
            )

        logger.info(f"SemanticChunker generated {len(chunks)} chunk(s) for document {document_id}")
        return chunks

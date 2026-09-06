"""
Context builder for assembling retrieved chunks and citations into grounded LLM prompt context.
"""

import logging
from typing import List, Optional, Tuple
from pydantic import BaseModel, Field

from rag.chunking.semantic_chunker import Chunk
from rag.context.citation_builder import CitationBuilder, Citation
from rag.context.deduplicator import ContextDeduplicator
from rag.context.context_compressor import ContextCompressor

logger = logging.getLogger(__name__)


class GroundedContextResult(BaseModel):
    """Container holding final formatted context string, citations, and source chunks."""
    query: str
    context_text: str
    citations: List[Citation] = Field(default_factory=list)
    retrieved_chunks: List[Chunk] = Field(default_factory=list)
    total_token_count: int = 0


class ContextBuilder:
    """Assembles retrieved passage chunks into structured grounded context."""

    def __init__(
        self,
        deduplicator: Optional[ContextDeduplicator] = None,
        citation_builder: Optional[CitationBuilder] = None,
        compressor: Optional[ContextCompressor] = None,
        enable_compression: bool = False,
    ):
        self.deduplicator = deduplicator or ContextDeduplicator()
        self.citation_builder = citation_builder or CitationBuilder()
        self.compressor = compressor or ContextCompressor()
        self.enable_compression = enable_compression

    def build_grounded_context(self, query: str, scored_chunks: List[Tuple[Chunk, float]]) -> GroundedContextResult:
        """Deduplicate, optionally compress, format, and attach citations to grounded context."""
        # 1. Deduplicate
        unique_chunks = self.deduplicator.deduplicate(scored_chunks)

        # 2. Build Citations
        citations = self.citation_builder.build_citations(unique_chunks)

        # 3. Format Context
        context_blocks: List[str] = []
        total_tokens = 0

        for (chunk, score), citation in zip(unique_chunks, citations):
            content = chunk.content
            if self.enable_compression:
                content = self.compressor.compress_text(content, query)

            header = citation.to_formatted_str()
            block = f"--- {header} ---\n{content}\n"
            context_blocks.append(block)
            total_tokens += len(content.split())

        final_context_str = "\n".join(context_blocks)
        raw_chunks = [chk for chk, _ in unique_chunks]

        logger.info(f"ContextBuilder built grounded context with {len(citations)} source passage(s) (~{total_tokens} tokens)")
        return GroundedContextResult(
            query=query,
            context_text=final_context_str,
            citations=citations,
            retrieved_chunks=raw_chunks,
            total_token_count=total_tokens,
        )

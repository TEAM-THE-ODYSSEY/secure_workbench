"""
Context package for deduplication, context assembly, optional compression, and traceable citation generation.
"""

from rag.context.deduplicator import ContextDeduplicator
from rag.context.context_builder import ContextBuilder, GroundedContextResult
from rag.context.context_compressor import ContextCompressor
from rag.context.citation_builder import CitationBuilder, Citation

__all__ = [
    "ContextDeduplicator",
    "ContextBuilder",
    "GroundedContextResult",
    "ContextCompressor",
    "CitationBuilder",
    "Citation",
]

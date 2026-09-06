"""
Chunk Repository for storing and querying text passage chunks in database storage.
"""

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from rag.chunking.semantic_chunker import Chunk

from rag.storage.postgres import ChunkModel, db_manager

logger = logging.getLogger(__name__)



class ChunkRepository:
    """Isolates database persistence operations for document chunks."""

    def __init__(self, session: Optional[Session] = None):
        self._external_session = session
        # Internal in-memory fallback list if DB session is in fallback mode
        self._local_chunks: Dict[str, Chunk] = {}

    def _get_session(self) -> Session:
        return self._external_session if self._external_session else db_manager.get_session()

    def save_chunk(self, chunk: Chunk) -> ChunkModel:
        """Persist a single Chunk to database."""
        self._local_chunks[chunk.chunk_id] = chunk
        session = self._get_session()
        try:
            # Ensure embedding is a native Python list of floats
            emb = [float(x) for x in chunk.embedding] if chunk.embedding is not None else None
            meta = dict(chunk.metadata) if chunk.metadata else {}

            chunk_model = session.query(ChunkModel).filter(ChunkModel.chunk_id == chunk.chunk_id).first()
            if not chunk_model:
                chunk_model = ChunkModel(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    version_id=chunk.version_id,
                    parent_chunk_id=chunk.parent_chunk_id,
                    chunk_type=chunk.chunk_type,
                    content=chunk.content,
                    page_number=chunk.page_number,
                    section_title=chunk.section_title,
                    chunk_index=chunk.chunk_index,
                    token_count=chunk.token_count,
                    metadata_json=meta,
                    embedding_json=emb,
                )
                session.add(chunk_model)
            else:
                chunk_model.content = chunk.content
                chunk_model.metadata_json = meta
                chunk_model.embedding_json = emb

            session.commit()
            return chunk_model
        except Exception as e:
            session.rollback()
            logger.error(f"DB save_chunk error ({e}). Stored in memory cache.", exc_info=True)
            return None
        finally:
            if not self._external_session:
                session.close()

    def save_batch(self, chunks: List[Chunk]) -> int:
        """Persist a batch of chunks."""
        saved_count = 0
        for chunk in chunks:
            self.save_chunk(chunk)
            saved_count += 1
        return saved_count

    def get_chunk_by_id(self, chunk_id: str) -> Optional[Chunk]:
        """Fetch chunk by chunk_id."""
        if chunk_id in self._local_chunks:
            return self._local_chunks[chunk_id]

        session = self._get_session()
        try:
            model = session.query(ChunkModel).filter(ChunkModel.chunk_id == chunk_id).first()
            if model:
                return Chunk(
                    chunk_id=model.chunk_id,
                    document_id=model.document_id,
                    version_id=model.version_id,
                    parent_chunk_id=model.parent_chunk_id,
                    chunk_type=model.chunk_type,
                    content=model.content,
                    page_number=model.page_number,
                    section_title=model.section_title,
                    chunk_index=model.chunk_index,
                    token_count=model.token_count,
                    metadata=model.metadata_json or {},
                    embedding=model.embedding_json,
                )
            return None
        finally:
            if not self._external_session:
                session.close()

    def get_chunks_by_document(self, document_id: str) -> List[Chunk]:
        """Fetch all chunks belonging to a document."""
        results = [c for c in self._local_chunks.values() if c.document_id == document_id]
        if results:
            return results

        session = self._get_session()
        try:
            models = session.query(ChunkModel).filter(ChunkModel.document_id == document_id).all()
            return [
                Chunk(
                    chunk_id=m.chunk_id,
                    document_id=m.document_id,
                    version_id=m.version_id,
                    parent_chunk_id=m.parent_chunk_id,
                    chunk_type=m.chunk_type,
                    content=m.content,
                    page_number=m.page_number,
                    section_title=m.section_title,
                    chunk_index=m.chunk_index,
                    token_count=m.token_count,
                    metadata=m.metadata_json or {},
                    embedding=m.embedding_json,
                )
                for m in models
            ]
        finally:
            if not self._external_session:
                session.close()

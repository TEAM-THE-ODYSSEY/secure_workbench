from __future__ import annotations

"""
PostgreSQL Full-Text Search (FTS) implementation using native tsvector and tsquery.
Replaces in-memory BM25 index for persistent, production-grade text retrieval.
"""


import logging
import json
import re
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING
from sqlalchemy import text
from sqlalchemy.orm import Session

from rag.chunking.semantic_chunker import Chunk
from rag.storage.postgres import DatabaseSessionManager

logger = logging.getLogger(__name__)



class PostgresFTSSearch:
    """
    Full-Text Search implementation using PostgreSQL native tsvector/tsquery indexing
    with in-memory keyword matching fallback.
    """

    def __init__(self, db_manager: Optional[DatabaseSessionManager] = None):
        self.db_manager = db_manager
        # In-memory document fallback store for testing or offline operation
        self._chunks: Dict[str, Chunk] = {}

    def add_chunk(self, chunk: Chunk) -> None:
        """Cache chunk in memory for fallback searching."""
        self._chunks[chunk.chunk_id] = chunk

    def add_chunks(self, chunks: List[Chunk]) -> None:
        """Cache list of chunks for fallback searching."""
        for c in chunks:
            self._chunks[c.chunk_id] = c

    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        session: Optional[Session] = None,
    ) -> List[Tuple[Chunk, float]]:
        """
        Execute full-text search against PostgreSQL chunks table.
        Falls back to in-memory term matching if database session is unavailable.
        """
        close_session = False
        if session is None and self.db_manager is not None:
            try:
                session = self.db_manager.get_session()
                close_session = True
            except Exception as e:
                logger.warning(f"Could not open DB session for FTS search: {e}")
                session = None

        if session is not None:
            try:
                results = self._search_db(session, query, top_k, filters)
                if results:
                    return results
            except Exception as e:
                logger.warning(f"PostgreSQL FTS DB query failed ({e}), falling back to in-memory search...")
            finally:
                if session and close_session:
                    session.close()

        return self._search_in_memory(query, top_k, filters)

    def _search_db(
        self,
        session: Session,
        query: str,
        top_k: int,
        filters: Optional[Dict[str, Any]],
    ) -> List[Tuple[Chunk, float]]:
        """Execute SQL query using tsvector and plainto_tsquery."""
        clean_query = query.strip()
        if not clean_query:
            return []

        where_clauses = ["to_tsvector('english', c.content) @@ plainto_tsquery('english', :query)"]
        params = {"query": clean_query, "top_k": top_k}

        if filters:
            if "trust_levels" in filters:
                trust_levels = filters["trust_levels"]
                if isinstance(trust_levels, list):
                    where_clauses.append("c.trust_level IN :trust_levels")
                    params["trust_levels"] = tuple(trust_levels)
            elif filters.get("exclude_untrusted"):
                where_clauses.append("c.trust_level NOT IN ('REJECTED', 'QUARANTINED')")

            if "document_id" in filters and filters["document_id"]:
                where_clauses.append("c.document_id = :doc_id")
                params["doc_id"] = filters["document_id"]

        where_sql = " AND ".join(where_clauses)
        sql = f"""
            SELECT c.chunk_id, c.document_id, c.version_id, c.content, c.page_number,
                   c.section_title, c.chunk_index, c.parent_chunk_id, c.chunk_type,
                   c.token_count, c.metadata_json, c.trust_level,
                   ts_rank_cd(to_tsvector('english', c.content), plainto_tsquery('english', :query)) AS rank
            FROM chunks c
            WHERE {where_sql}
            ORDER BY rank DESC
            LIMIT :top_k
        """

        result = session.execute(text(sql), params)
        rows = result.fetchall()

        results: List[Tuple[Chunk, float]] = []
        for row in rows:
            meta = row[10] or {}
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except Exception:
                    meta = {}
            meta["trust_level"] = row[11]

            chunk = Chunk(
                chunk_id=row[0],
                document_id=row[1],
                version_id=row[2],
                content=row[3],
                page_number=row[4] or 1,
                section_title=row[5] or "General",
                chunk_index=row[6] or 0,
                parent_chunk_id=row[7],
                chunk_type=row[8] or "child",
                token_count=row[9] or 0,
                metadata=meta,
            )
            score = float(row[12]) if row[12] is not None else 0.0
            results.append((chunk, score))
        return results

    def _search_in_memory(
        self,
        query: str,
        top_k: int,
        filters: Optional[Dict[str, Any]],
    ) -> List[Tuple[Chunk, float]]:
        """Simple in-memory term frequency search fallback."""
        query_terms = set(re.findall(r"\w+", query.lower()))
        if not query_terms:
            return []

        results: List[Tuple[Chunk, float]] = []

        for chunk_id, chunk in self._chunks.items():
            if filters:
                chunk_meta = chunk.metadata or {}
                if filters.get("exclude_untrusted"):
                    trust = chunk_meta.get("trust_level", "UNTRUSTED")
                    if trust in ("REJECTED", "QUARANTINED"):
                        continue

            doc_terms = re.findall(r"\w+", chunk.content.lower())
            if not doc_terms:
                continue

            matches = sum(1 for term in query_terms if term in doc_terms)
            if matches > 0:
                score = float(matches) / float(len(query_terms))
                results.append((chunk, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def clear(self) -> None:
        """Clear cached in-memory chunks."""
        self._chunks.clear()

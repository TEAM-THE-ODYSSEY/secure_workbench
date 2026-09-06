from __future__ import annotations

"""
pgvector storage abstraction for vector indexing, cosine similarity, and native PostgreSQL vector queries.
"""


import logging
import json
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING
import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from rag.chunking.semantic_chunker import Chunk

from rag.storage.postgres import DatabaseSessionManager

logger = logging.getLogger(__name__)



def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Calculate cosine similarity between two numeric vectors."""
    a = np.array(vec_a, dtype=float)
    b = np.array(vec_b, dtype=float)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


class PgVectorStore:
    """
    Abstraction for pgvector operations and vector similarity queries using PostgreSQL native pgvector extension
    with in-memory fallback cache.
    """

    def __init__(self, dimension: int = 1024, db_manager: Optional[DatabaseSessionManager] = None):
        self.dimension = dimension
        self.db_manager = db_manager
        # In-memory vector cache for fallback or local testing
        self._vector_store: Dict[str, Tuple[Chunk, List[float]]] = {}

    def insert_chunk_vector(
        self,
        chunk: Chunk,
        vector: List[float],
        session: Optional[Session] = None,
    ) -> None:
        """Store chunk and vector representation in both DB and in-memory cache."""
        chunk.embedding = vector
        self._vector_store[chunk.chunk_id] = (chunk, vector)

        close_session = False
        if session is None and self.db_manager is not None:
            try:
                session = self.db_manager.get_session()
                close_session = True
            except Exception as e:
                logger.warning(f"Could not open DB session for vector insert: {e}")

        if session is not None:
            try:
                vec_str = f"[{','.join(str(x) for x in vector)}]"
                query = text("""
                    UPDATE chunks
                    SET embedding_json = :vec_json
                    WHERE chunk_id = :chunk_id
                """)
                session.execute(query, {
                    "vec_json": json.dumps(vector),
                    "chunk_id": chunk.chunk_id,
                })
                try:
                    query_vec = text("""
                        UPDATE chunks
                        SET embedding = :vec_str::vector
                        WHERE chunk_id = :chunk_id
                    """)
                    session.execute(query_vec, {
                        "vec_str": vec_str,
                        "chunk_id": chunk.chunk_id,
                    })
                except Exception:
                    pass  # column vector might not exist yet if migration pending
                session.commit()
            except Exception as e:
                logger.error(f"Error inserting chunk vector into database: {e}")
                if session and close_session:
                    session.rollback()
            finally:
                if session and close_session:
                    session.close()

    def search_similar(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        session: Optional[Session] = None,
    ) -> List[Tuple[Chunk, float]]:
        """
        Perform similarity search matching vector and metadata filters.
        Queries native pgvector in PostgreSQL if available, otherwise falls back to in-memory search.
        """
        close_session = False
        if session is None and self.db_manager is not None:
            try:
                session = self.db_manager.get_session()
                close_session = True
            except Exception:
                session = None

        if session is not None:
            try:
                db_results = self._search_db(session, query_vector, top_k, filters)
                if db_results:
                    return db_results
            except Exception as e:
                logger.warning(f"Native pgvector DB search failed ({e}), falling back to in-memory store...")
            finally:
                if session and close_session:
                    session.close()

        return self._search_in_memory(query_vector, top_k, filters)

    def _search_db(
        self,
        session: Session,
        query_vector: List[float],
        top_k: int,
        filters: Optional[Dict[str, Any]],
    ) -> List[Tuple[Chunk, float]]:
        """Native SQL search using pgvector cosine distance operator `<=>`."""
        vec_str = f"[{','.join(str(x) for x in query_vector)}]"
        where_clauses = ["c.embedding IS NOT NULL"]
        params = {"vec_str": vec_str, "top_k": top_k}

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
                   1 - (c.embedding <=> CAST(:vec_str AS vector)) AS similarity
            FROM chunks c
            WHERE {where_sql}
            ORDER BY c.embedding <=> CAST(:vec_str AS vector)
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
        query_vector: List[float],
        top_k: int,
        filters: Optional[Dict[str, Any]],
    ) -> List[Tuple[Chunk, float]]:
        """Perform in-memory similarity search."""
        results: List[Tuple[Chunk, float]] = []

        for chunk_id, (chunk, vector) in self._vector_store.items():
            if filters:
                match = True
                chunk_meta = chunk.metadata or {}

                if filters.get("exclude_untrusted"):
                    trust = chunk_meta.get("trust_level", "UNTRUSTED")
                    if trust in ("REJECTED", "QUARANTINED"):
                        continue
                if "trust_levels" in filters:
                    trust = chunk_meta.get("trust_level", "UNTRUSTED")
                    if trust not in filters["trust_levels"]:
                        continue

                for key, val in filters.items():
                    if key in ("exclude_untrusted", "trust_levels"):
                        continue
                    if val is not None:
                        chunk_val = chunk_meta.get(key)
                        if isinstance(val, str) and isinstance(chunk_val, str):
                            if val.lower() != chunk_val.lower():
                                match = False
                                break
                        elif chunk_val != val:
                            match = False
                            break
                if not match:
                    continue

            score = cosine_similarity(query_vector, vector)
            results.append((chunk, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def clear(self) -> None:
        """Clear cached vectors."""
        self._vector_store.clear()

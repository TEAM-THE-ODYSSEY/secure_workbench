"""
Trust-aware filtering layer for retrieved document chunks.
Ensures quarantined, rejected, or compromised documents are strictly excluded from downstream retrieval context.
"""

import logging
from typing import List, Optional, Set, Tuple

from rag.chunking.semantic_chunker import Chunk
from rag.storage.postgres import TrustLevel

logger = logging.getLogger(__name__)


class TrustFilter:
    """
    Post-retrieval filter enforcing trust boundaries and quarantine isolation.
    """

    # Untrusted/quarantined trust statuses that must never enter RAG context
    BLOCKED_TRUST_LEVELS: Set[str] = {
        TrustLevel.QUARANTINED.value,
        TrustLevel.REVOKED.value,
        "QUARANTINED",
        "REJECTED",
        "REVOKED",
        "MALICIOUS",
    }


    def __init__(self, allowed_trust_levels: Optional[List[str]] = None):
        """
        :param allowed_trust_levels: If provided, only chunks matching these levels pass.
        """
        self.allowed_trust_levels = allowed_trust_levels

    def filter_chunks(
        self,
        candidate_chunks: List[Tuple[Chunk, float]],
    ) -> List[Tuple[Chunk, float]]:
        """
        Filter candidate (Chunk, score) tuples based on trust metadata.
        Returns only clean, non-quarantined chunks.
        """
        filtered: List[Tuple[Chunk, float]] = []

        for chunk, score in candidate_chunks:
            meta = chunk.metadata or {}
            chunk_trust = meta.get("trust_level", TrustLevel.UNTRUSTED.value).upper()
            doc_status = meta.get("status", "ACTIVE").upper()

            # 1. Reject blocked trust levels
            if chunk_trust in self.BLOCKED_TRUST_LEVELS:
                logger.warning(
                    f"TrustFilter blocked chunk {chunk.chunk_id} from doc {chunk.document_id}: "
                    f"trust_level={chunk_trust}"
                )
                continue

            # 2. Reject quarantined or revoked document status
            if doc_status in ("QUARANTINED", "REJECTED", "REVOKED", "ARCHIVED"):
                logger.warning(
                    f"TrustFilter blocked chunk {chunk.chunk_id} from doc {chunk.document_id}: "
                    f"doc_status={doc_status}"
                )
                continue

            # 3. Check allowed list if specified
            if self.allowed_trust_levels:
                allowed_upper = {t.upper() for t in self.allowed_trust_levels}
                if chunk_trust not in allowed_upper:
                    logger.debug(
                        f"TrustFilter excluded chunk {chunk.chunk_id}: trust_level={chunk_trust} not in {allowed_upper}"
                    )
                    continue

            filtered.append((chunk, score))

        logger.info(f"TrustFilter passed {len(filtered)} out of {len(candidate_chunks)} candidate chunks.")
        return filtered

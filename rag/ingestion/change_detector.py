"""
Change detector for evaluating document status (NEW, MODIFIED, DELETED, UNCHANGED)
to enable incremental RAG indexing.
"""

from enum import Enum
import logging
from typing import Dict, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class DocumentChangeState(str, Enum):
    NEW = "NEW"
    MODIFIED = "MODIFIED"
    DELETED = "DELETED"
    UNCHANGED = "UNCHANGED"


class ChangeResult(BaseModel):
    source_id: str
    state: DocumentChangeState
    previous_checksum: Optional[str] = None
    current_checksum: Optional[str] = None


class ChangeDetector:
    """Detects document state changes by comparing current checksums against a registered manifest or database repo."""

    def __init__(self, known_checksums: Optional[Dict[str, str]] = None):
        # map of source_id -> sha256 checksum
        self._known_checksums: Dict[str, str] = known_checksums or {}

    def register_known_documents(self, checksum_map: Dict[str, str]) -> None:
        """Update internal store of known document checksums."""
        self._known_checksums.update(checksum_map)

    def detect_change(self, source_id: str, current_checksum: Optional[str]) -> ChangeResult:
        """Determine change status for a document given its current checksum."""
        prev_checksum = self._known_checksums.get(source_id)

        if current_checksum is None:
            if prev_checksum is not None:
                return ChangeResult(
                    source_id=source_id,
                    state=DocumentChangeState.DELETED,
                    previous_checksum=prev_checksum,
                    current_checksum=None,
                )
            else:
                return ChangeResult(
                    source_id=source_id,
                    state=DocumentChangeState.UNCHANGED,
                    previous_checksum=None,
                    current_checksum=None,
                )

        if prev_checksum is None:
            return ChangeResult(
                source_id=source_id,
                state=DocumentChangeState.NEW,
                previous_checksum=None,
                current_checksum=current_checksum,
            )

        if prev_checksum != current_checksum:
            return ChangeResult(
                source_id=source_id,
                state=DocumentChangeState.MODIFIED,
                previous_checksum=prev_checksum,
                current_checksum=current_checksum,
            )

        return ChangeResult(
            source_id=source_id,
            state=DocumentChangeState.UNCHANGED,
            previous_checksum=prev_checksum,
            current_checksum=current_checksum,
        )

    def mark_indexed(self, source_id: str, checksum: str) -> None:
        """Record successful indexing of document checksum."""
        self._known_checksums[source_id] = checksum

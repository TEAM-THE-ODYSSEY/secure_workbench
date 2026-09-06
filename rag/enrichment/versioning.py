"""
Document version management for tracking document revisions and filtering out outdated versions during retrieval.
"""

from datetime import datetime, timezone
import logging
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DocumentVersionRecord(BaseModel):
    """Record tracking a specific version of a document."""
    version_id: str
    document_id: str
    revision_code: str  # e.g., R0, R1, Rev-A, v1.2
    checksum: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True
    superseded_by_version_id: Optional[str] = None
    change_summary: str = ""


class DocumentVersionManager:
    """Manages lifecycle of document revisions and handles revision state transition."""

    def __init__(self):
        # map document_id -> List[DocumentVersionRecord]
        self._version_registry: Dict[str, List[DocumentVersionRecord]] = {}

    def register_new_version(
        self,
        document_id: str,
        revision_code: str,
        checksum: str,
        change_summary: str = ""
    ) -> DocumentVersionRecord:
        """Register a new version of a document, marking previous active version as superseded."""
        versions = self._version_registry.setdefault(document_id, [])
        version_num = len(versions) + 1
        new_version_id = f"{document_id}_v{version_num}"

        # Deactivate previous active version
        for v in versions:
            if v.is_active:
                v.is_active = False
                v.superseded_by_version_id = new_version_id
                logger.info(f"Superseded version {v.version_id} with new version {new_version_id}")

        new_record = DocumentVersionRecord(
            version_id=new_version_id,
            document_id=document_id,
            revision_code=revision_code,
            checksum=checksum,
            is_active=True,
            change_summary=change_summary,
        )
        versions.append(new_record)
        return new_record

    def get_active_version(self, document_id: str) -> Optional[DocumentVersionRecord]:
        """Get current active version for a document ID."""
        versions = self._version_registry.get(document_id, [])
        for v in versions:
            if v.is_active:
                return v
        return None

    def is_version_active(self, document_id: str, version_id: str) -> bool:
        """Check if a specific version ID is the active active revision."""
        active = self.get_active_version(document_id)
        return active is not None and active.version_id == version_id

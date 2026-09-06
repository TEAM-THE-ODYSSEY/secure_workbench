from __future__ import annotations

"""
Metadata Repository for indexing and querying metadata attributes.
"""

import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from rag.storage.postgres import MetadataModel, db_manager

logger = logging.getLogger(__name__)


class MetadataRepository:
    """Isolates database operations for metadata search and attributes."""

    def __init__(self, session: Optional[Session] = None):
        self._external_session = session

    def _get_session(self) -> Session:
        return self._external_session if self._external_session else db_manager.get_session()

    def add_metadata_entries(self, document_id: str, metadata_dict: Dict[str, Any]) -> None:
        """Add flattened metadata entries for a document."""
        session = self._get_session()
        try:
            for k, v in metadata_dict.items():
                if v is not None:
                    val_str = str(v)
                    entry = MetadataModel(document_id=document_id, key=k, value=val_str)
                    session.add(entry)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.debug(f"MetadataRepository notice ({e})")
        finally:
            if not self._external_session:
                session.close()

    def get_document_metadata(self, document_id: str) -> Dict[str, str]:
        """Fetch metadata key-value dictionary for document."""
        session = self._get_session()
        try:
            entries = session.query(MetadataModel).filter(MetadataModel.document_id == document_id).all()
            return {e.key: e.value for e in entries}
        finally:
            if not self._external_session:
                session.close()

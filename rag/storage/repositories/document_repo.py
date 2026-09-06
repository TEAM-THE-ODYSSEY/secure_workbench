"""
Document Repository for encapsulating document and document version database transactions.
"""

import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from rag.enrichment.metadata import DocumentMetadata
from rag.storage.postgres import DocumentModel, DocumentVersionModel, db_manager

logger = logging.getLogger(__name__)


class DocumentRepository:
    """Isolates database operations for documents and version history."""

    def __init__(self, session: Optional[Session] = None):
        self._external_session = session

    def _get_session(self) -> Session:
        return self._external_session if self._external_session else db_manager.get_session()

    def upsert_document(self, metadata: DocumentMetadata, checksum: str, filename: str, extension: str) -> DocumentModel:
        """Create or update a document record in the database."""
        session = self._get_session()
        try:
            doc = session.query(DocumentModel).filter(DocumentModel.source_id == metadata.document_id).first()
            if not doc:
                doc = DocumentModel(
                    id=metadata.document_id,
                    source_id=metadata.document_id,
                    filename=filename,
                    extension=extension,
                    document_type=metadata.document_type,
                    department=metadata.department,
                    plant=metadata.plant,
                    unit=metadata.unit,
                    equipment_id=metadata.equipment_id,
                    checksum=checksum,
                )
                session.add(doc)
            else:
                doc.filename = filename
                doc.extension = extension
                doc.document_type = metadata.document_type
                doc.department = metadata.department
                doc.plant = metadata.plant
                doc.unit = metadata.unit
                doc.equipment_id = metadata.equipment_id
                doc.checksum = checksum

            session.commit()
            return doc
        except Exception as e:
            session.rollback()
            logger.error(f"Error upserting document {metadata.document_id}: {e}", exc_info=True)
            raise e
        finally:
            if not self._external_session:
                session.close()

    def get_by_source_id(self, source_id: str) -> Optional[DocumentModel]:
        """Fetch document by source_id."""
        session = self._get_session()
        try:
            return session.query(DocumentModel).filter(DocumentModel.source_id == source_id).first()
        finally:
            if not self._external_session:
                session.close()

    def add_version(self, version_record: Any) -> DocumentVersionModel:
        """Create a version record."""
        session = self._get_session()
        try:
            ver_model = DocumentVersionModel(
                version_id=version_record.version_id,
                document_id=version_record.document_id,
                revision_code=version_record.revision_code,
                checksum=version_record.checksum,
                is_active=version_record.is_active,
                change_summary=version_record.change_summary,
            )
            session.add(ver_model)
            session.commit()
            return ver_model
        except Exception as e:
            session.rollback()
            logger.error(f"Error adding document version: {e}", exc_info=True)
            raise e
        finally:
            if not self._external_session:
                session.close()

    def list_documents(self) -> List[DocumentModel]:
        """List all documents."""
        session = self._get_session()
        try:
            return session.query(DocumentModel).all()
        finally:
            if not self._external_session:
                session.close()

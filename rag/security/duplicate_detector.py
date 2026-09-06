import logging
from typing import Optional
from pydantic import BaseModel
from rag.storage.postgres import db_manager, DocumentModel

logger = logging.getLogger(__name__)

class DuplicateCheckResult(BaseModel):
    is_duplicate: bool
    duplicate_document_id: Optional[str] = None
    similarity: float = 0.0

class DuplicateDetector:
    def check_duplicate(self, content_hash: str) -> DuplicateCheckResult:
        logger.info(f"Checking duplicate for hash {content_hash}")
        session = db_manager.get_session()
        try:
            existing_doc = session.query(DocumentModel).filter(DocumentModel.content_hash == content_hash).first()
            if existing_doc:
                return DuplicateCheckResult(
                    is_duplicate=True,
                    duplicate_document_id=existing_doc.id,
                    similarity=1.0
                )
            return DuplicateCheckResult(is_duplicate=False, similarity=0.0)
        except Exception as e:
            logger.error(f"Duplicate check failed: {e}")
            return DuplicateCheckResult(is_duplicate=False)
        finally:
            session.close()

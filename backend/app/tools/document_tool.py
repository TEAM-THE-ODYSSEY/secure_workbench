"""
DocumentTool for querying document metadata, structure summaries, and page details.
"""

import logging
from typing import Any, Dict, List, Optional
from agent.tools.base import BaseTool
from rag.storage.postgres import db_manager, DocumentModel, ChunkModel

logger = logging.getLogger("agent.tools.document_tool")


class DocumentTool(BaseTool):
    """Capability Tool for retrieving document-level metadata and page summaries."""

    @property
    def name(self) -> str:
        return "document_info"

    @property
    def description(self) -> str:
        return "Retrieve document metadata, file IDs, version histories, and structure summaries."

    def execute(self, **kwargs) -> Dict[str, Any]:
        doc_id = kwargs.get("document_id")
        title = kwargs.get("title")
        session = db_manager.get_session()

        try:
            query = session.query(DocumentModel)
            if doc_id:
                query = query.filter(DocumentModel.id == doc_id)
            elif title:
                query = query.filter(DocumentModel.title.ilike(f"%{title}%"))

            doc = query.first()
            if not doc:
                return {"status": "NOT_FOUND", "message": f"No document matching criteria (id={doc_id}, title={title})"}

            chunk_count = session.query(ChunkModel).filter(ChunkModel.document_id == doc.id).count()

            return {
                "status": "SUCCESS",
                "document_id": doc.id,
                "title": doc.title,
                "document_type": doc.document_type,
                "status_approval": doc.status,
                "total_chunks": chunk_count,
            }
        finally:
            session.close()

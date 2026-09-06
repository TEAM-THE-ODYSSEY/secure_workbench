from __future__ import annotations

"""Append-only audit log repository for system-wide traceability."""

import logging
from typing import List, Optional
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from rag.storage.postgres import AuditRecordModel

logger = logging.getLogger(__name__)


class AuditRepository:
    """Append-only audit log persistence."""

    def log_action(
        self,
        session: Session,
        action: str,
        actor: Optional[str] = None,
        document_id: Optional[str] = None,
        details: dict = None,
    ) -> AuditRecordModel:
        record = AuditRecordModel(
            record_id=str(uuid.uuid4()),
            action=action,
            actor=actor or "system",
            document_id=document_id,
            details_json=details or {},
            timestamp=datetime.now(timezone.utc),
        )
        session.add(record)
        session.flush()
        return record

    def record_action(
        self,
        session: Session,
        action: str,
        actor: Optional[str] = None,
        document_id: Optional[str] = None,
        job_id: Optional[str] = None,
        details: dict = None,
    ) -> AuditRecordModel:
        det = details or {}
        if job_id:
            det["job_id"] = job_id
        return self.log_action(
            session=session,
            action=action,
            actor=actor,
            document_id=document_id,
            details=det,
        )

    def get_audit_trail(
        self,
        session: Session,
        document_id: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 100,
    ) -> List[AuditRecordModel]:
        query = session.query(AuditRecordModel)
        if document_id:
            query = query.filter_by(document_id=document_id)
        if action:
            query = query.filter_by(action=action)
        return query.order_by(AuditRecordModel.timestamp.desc()).limit(limit).all()

    def get_recent_actions(self, session: Session, limit: int = 50) -> List[AuditRecordModel]:
        return (
            session.query(AuditRecordModel)
            .order_by(AuditRecordModel.timestamp.desc())
            .limit(limit)
            .all()
        )

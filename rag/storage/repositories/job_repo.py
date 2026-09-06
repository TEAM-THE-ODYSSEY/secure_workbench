from __future__ import annotations

"""Repository for ingestion job lifecycle management."""

import logging
from datetime import datetime, timezone
from typing import Any, List, Optional
import uuid

from sqlalchemy.orm import Session

from rag.storage.postgres import IngestionJobModel, JobStatus

logger = logging.getLogger(__name__)


class JobRepository:
    """CRUD and status transitions for ingestion jobs."""

    def create_job(
        self,
        session: Session,
        filename: str = "document",
        source_id: Optional[str] = None,
        file_hash: Optional[str] = None,
        file_size_bytes: int = 0,
        job_id: Optional[str] = None,
        status: Optional[Any] = None,
    ) -> IngestionJobModel:
        j_id = job_id or f"job_{uuid.uuid4().hex[:12]}"
        st = status.value if hasattr(status, "value") else (status or JobStatus.ACCEPTED.value)
        job = IngestionJobModel(
            job_id=j_id,
            source_id=source_id,
            filename=filename,
            file_hash=file_hash,
            file_size_bytes=file_size_bytes,
            status=st,
        )
        session.add(job)
        session.flush()
        logger.info(f"Created ingestion job {job.job_id} for '{filename}'")
        return job

    def get_by_id(self, session: Session, job_id: str) -> Optional[IngestionJobModel]:
        return session.query(IngestionJobModel).filter_by(job_id=job_id).first()

    def update_status(
        self,
        session: Session,
        job_id: str,
        status: Any,
        error_message: Optional[str] = None,
        document_id: Optional[str] = None,
        celery_task_id: Optional[str] = None,
        security_summary: Optional[dict] = None,
        progress: Optional[float] = None,
    ) -> Optional[IngestionJobModel]:
        job = self.get_by_id(session, job_id)
        if not job:
            logger.warning(f"Job {job_id} not found for status update")
            return None

        job.status = status.value if hasattr(status, "value") else str(status)
        job.updated_at = datetime.now(timezone.utc)

        if progress is not None:
            job.progress = progress
        if error_message is not None:
            job.error_message = error_message
        if document_id is not None:
            job.document_id = document_id
        if celery_task_id is not None:
            job.celery_task_id = celery_task_id
        if security_summary is not None:
            job.security_summary = security_summary
        if str(job.status) in ("COMPLETED", "FAILED", "QUARANTINED"):
            job.completed_at = datetime.now(timezone.utc)

        session.flush()
        logger.info(f"Job {job_id} status updated to {job.status}")
        return job

    def list_jobs(
        self,
        session: Session,
        status: Optional[JobStatus] = None,
        limit: int = 50,
    ) -> List[IngestionJobModel]:
        query = session.query(IngestionJobModel)
        if status:
            query = query.filter_by(status=status.value)
        return query.order_by(IngestionJobModel.created_at.desc()).limit(limit).all()

    def get_recent_jobs(self, session: Session, limit: int = 20) -> List[IngestionJobModel]:
        return (
            session.query(IngestionJobModel)
            .order_by(IngestionJobModel.created_at.desc())
            .limit(limit)
            .all()
        )

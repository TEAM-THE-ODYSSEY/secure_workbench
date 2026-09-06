"""Repository for security findings persistence and querying."""

import logging
from typing import List, Optional
import uuid

from sqlalchemy.orm import Session

from rag.storage.postgres import SecurityFindingModel, FindingType, FindingSeverity

logger = logging.getLogger(__name__)


class SecurityRepository:
    """Persist and query security findings from the security pipeline."""

    def create_finding(
        self,
        session: Session,
        document_id: str,
        finding_type: FindingType,
        severity: FindingSeverity,
        description: str,
        job_id: Optional[str] = None,
        details_json: dict = None,
    ) -> SecurityFindingModel:
        finding = SecurityFindingModel(
            finding_id=str(uuid.uuid4()),
            document_id=document_id,
            job_id=job_id,
            finding_type=finding_type.value,
            severity=severity.value,
            description=description,
            details_json=details_json or {},
        )
        session.add(finding)
        session.flush()
        logger.info(
            f"Security finding [{severity.value}] {finding_type.value}: {description[:80]}..."
        )
        return finding

    def create_findings_batch(
        self, session: Session, findings: List[dict]
    ) -> List[SecurityFindingModel]:
        """Batch create security findings. Each dict should have document_id, finding_type, severity, description, etc."""
        results = []
        for f in findings:
            results.append(self.create_finding(
                session,
                document_id=f["document_id"],
                finding_type=FindingType(f["finding_type"]),
                severity=FindingSeverity(f["severity"]),
                description=f["description"],
                job_id=f.get("job_id"),
                details_json=f.get("details_json", {}),
            ))
        return results

    def get_findings_for_document(
        self, session: Session, document_id: str
    ) -> List[SecurityFindingModel]:
        return (
            session.query(SecurityFindingModel)
            .filter_by(document_id=document_id)
            .order_by(SecurityFindingModel.created_at.desc())
            .all()
        )

    def get_findings_for_job(
        self, session: Session, job_id: str
    ) -> List[SecurityFindingModel]:
        return (
            session.query(SecurityFindingModel)
            .filter_by(job_id=job_id)
            .order_by(SecurityFindingModel.created_at.desc())
            .all()
        )

    def get_findings_by_type(
        self, session: Session, finding_type: FindingType, limit: int = 50
    ) -> List[SecurityFindingModel]:
        return (
            session.query(SecurityFindingModel)
            .filter_by(finding_type=finding_type.value)
            .order_by(SecurityFindingModel.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_critical_findings(
        self, session: Session, limit: int = 50
    ) -> List[SecurityFindingModel]:
        return (
            session.query(SecurityFindingModel)
            .filter(SecurityFindingModel.severity.in_([
                FindingSeverity.CRITICAL.value,
                FindingSeverity.HIGH.value,
            ]))
            .order_by(SecurityFindingModel.created_at.desc())
            .limit(limit)
            .all()
        )

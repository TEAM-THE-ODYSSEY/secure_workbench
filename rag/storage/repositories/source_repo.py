from __future__ import annotations

"""Repository for ingestion source CRUD operations."""

import logging
from datetime import datetime, timezone
from typing import List, Optional
import uuid

from sqlalchemy.orm import Session

from rag.storage.postgres import SourceModel, TrustLevel, SourceType

logger = logging.getLogger(__name__)


class SourceRepository:
    """CRUD operations for ingestion sources."""

    def create_source(
        self,
        session: Session,
        name: str,
        source_type: SourceType = SourceType.ADMIN_UPLOAD,
        trust_level: TrustLevel = TrustLevel.UNTRUSTED,
        config_json: dict = None,
    ) -> SourceModel:
        source = SourceModel(
            source_id=str(uuid.uuid4()),
            name=name,
            source_type=source_type.value,
            trust_level=trust_level.value,
            config_json=config_json or {},
        )
        session.add(source)
        session.flush()
        logger.info(f"Created source '{name}' (id={source.source_id}, trust={trust_level.value})")
        return source

    def get_by_id(self, session: Session, source_id: str) -> Optional[SourceModel]:
        return session.query(SourceModel).filter_by(source_id=source_id).first()

    def get_by_name(self, session: Session, name: str) -> Optional[SourceModel]:
        return session.query(SourceModel).filter_by(name=name).first()

    def get_or_create_admin_source(self, session: Session) -> SourceModel:
        """Get or create the default admin upload source."""
        source = self.get_by_name(session, "admin_upload")
        if source is None:
            source = self.create_source(
                session,
                name="admin_upload",
                source_type=SourceType.ADMIN_UPLOAD,
                trust_level=TrustLevel.TRUSTED,
            )
        return source

    def update_trust_level(
        self, session: Session, source_id: str, trust_level: TrustLevel
    ) -> Optional[SourceModel]:
        source = self.get_by_id(session, source_id)
        if source:
            source.trust_level = trust_level.value
            source.updated_at = datetime.now(timezone.utc)
            session.flush()
            logger.info(f"Updated source {source_id} trust to {trust_level.value}")
        return source

    def list_sources(self, session: Session) -> List[SourceModel]:
        return session.query(SourceModel).order_by(SourceModel.created_at.desc()).all()

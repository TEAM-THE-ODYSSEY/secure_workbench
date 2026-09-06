"""Repository for canonical entity management and entity-chunk linking."""

import logging
from typing import List, Optional
import uuid

from sqlalchemy.orm import Session

from rag.storage.postgres import EntityModel, EntityRelationshipModel, ChunkEntityModel

logger = logging.getLogger(__name__)


class EntityRepository:
    """CRUD for entities, aliases, and entity-chunk relationships."""

    def upsert_entity(
        self,
        session: Session,
        canonical_name: str,
        entity_type: str,
        aliases: List[str] = None,
        metadata: dict = None,
    ) -> EntityModel:
        """Create or update a canonical entity."""
        entity = session.query(EntityModel).filter_by(canonical_name=canonical_name).first()
        if entity:
            if aliases:
                existing_aliases = set(entity.aliases_json or [])
                existing_aliases.update(aliases)
                entity.aliases_json = list(existing_aliases)
            if metadata:
                merged_meta = entity.metadata_json or {}
                merged_meta.update(metadata)
                entity.metadata_json = merged_meta
            session.flush()
            return entity

        entity = EntityModel(
            entity_id=str(uuid.uuid4()),
            canonical_name=canonical_name,
            entity_type=entity_type,
            aliases_json=aliases or [],
            metadata_json=metadata or {},
        )
        session.add(entity)
        session.flush()
        logger.info(f"Created entity '{canonical_name}' (type={entity_type}, id={entity.entity_id})")
        return entity

    def get_by_id(self, session: Session, entity_id: str) -> Optional[EntityModel]:
        return session.query(EntityModel).filter_by(entity_id=entity_id).first()

    def get_by_canonical_name(self, session: Session, canonical_name: str) -> Optional[EntityModel]:
        return session.query(EntityModel).filter_by(canonical_name=canonical_name).first()

    def search_entities(
        self, session: Session, query: str, entity_type: Optional[str] = None, limit: int = 20
    ) -> List[EntityModel]:
        """Search entities by name or alias."""
        q = session.query(EntityModel).filter(
            EntityModel.canonical_name.ilike(f"%{query}%")
        )
        if entity_type:
            q = q.filter_by(entity_type=entity_type)
        return q.limit(limit).all()

    def link_chunk_to_entity(
        self, session: Session, chunk_id: str, entity_id: str, confidence: float = 1.0
    ) -> ChunkEntityModel:
        """Link a chunk to a canonical entity."""
        existing = (
            session.query(ChunkEntityModel)
            .filter_by(chunk_id=chunk_id, entity_id=entity_id)
            .first()
        )
        if existing:
            existing.confidence = max(existing.confidence, confidence)
            session.flush()
            return existing

        link = ChunkEntityModel(chunk_id=chunk_id, entity_id=entity_id, confidence=confidence)
        session.add(link)
        session.flush()
        return link

    def link_chunks_batch(
        self, session: Session, links: List[dict]
    ) -> List[ChunkEntityModel]:
        """Batch link chunks to entities. Each dict: {chunk_id, entity_id, confidence}."""
        results = []
        for link_data in links:
            results.append(self.link_chunk_to_entity(
                session,
                chunk_id=link_data["chunk_id"],
                entity_id=link_data["entity_id"],
                confidence=link_data.get("confidence", 1.0),
            ))
        return results

    def add_entity_relationship(
        self,
        session: Session,
        source_entity_id: str,
        target_entity_id: str,
        relationship_type: str,
        confidence: float = 1.0,
        source_document_id: Optional[str] = None,
    ) -> EntityRelationshipModel:
        rel = EntityRelationshipModel(
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            relationship_type=relationship_type,
            confidence=confidence,
            source_document_id=source_document_id,
        )
        session.add(rel)
        session.flush()
        return rel

    def get_entity_chunks(self, session: Session, entity_id: str) -> List[ChunkEntityModel]:
        return session.query(ChunkEntityModel).filter_by(entity_id=entity_id).all()

    def get_entities_by_type(self, session: Session, entity_type: str) -> List[EntityModel]:
        return session.query(EntityModel).filter_by(entity_type=entity_type).all()

    def list_entities(self, session: Session, limit: int = 100) -> List[EntityModel]:
        return session.query(EntityModel).order_by(EntityModel.canonical_name).limit(limit).all()

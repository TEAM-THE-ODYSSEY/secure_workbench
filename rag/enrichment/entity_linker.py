"""
Canonical Entity Linker for resolving extracted text mentions to canonical database entities.
Handles alias normalization and links document chunks to entities in PostgreSQL.
"""

import logging
import re
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from rag.enrichment.entity_extractor import ExtractedEntity, EntityType
from rag.storage.repositories.entity_repo import EntityRepository
from rag.storage.postgres import EntityModel

logger = logging.getLogger(__name__)


class EntityLinker:
    """
    Resolves extracted entity mentions to canonical entity records, managing alias maps
    and chunk-entity relationship links.
    """

    # Static alias maps for refinery equipment & units
    ALIAS_MAP: Dict[str, str] = {
        "CDU-1": "CDU",
        "CDU1": "CDU",
        "CRUDE DISTILLATION UNIT": "CDU",
        "VACUUM DISTILLATION UNIT": "VDU",
        "VDU-1": "VDU",
        "DIESEL HYDRODESULPHURISATION": "DHDS",
        "DHDS-1": "DHDS",
        "HYDROCRACKER": "HCU",
        "CONTINUOUS CATALYTIC REFORMER": "CCR",
        "FLUID CATALYTIC CRACKER": "FCCU",
    }

    def __init__(self, entity_repo: Optional[EntityRepository] = None):
        self.entity_repo = entity_repo or EntityRepository()

    def canonicalize_name(self, raw_name: str, entity_type: EntityType) -> str:
        """Clean and normalize raw entity text into canonical form."""
        name = raw_name.strip().upper()

        # Remove extra whitespace and leading punctuation
        name = re.sub(r"\s+", " ", name)
        name = re.sub(r"^(EQUIPMENT|TAG|UNIT)\s*#?\s*", "", name)

        # Check explicit alias dictionary
        if name in self.ALIAS_MAP:
            return self.ALIAS_MAP[name]

        return name

    def link_entities_for_chunk(
        self,
        chunk_id: str,
        extracted_entities: List[ExtractedEntity],
        session: Optional[Session] = None,
    ) -> List[Dict[str, str]]:
        """
        Resolve extracted entities to canonical entities and persist chunk-entity links in DB.
        """
        linked_records: List[Dict[str, str]] = []

        if not extracted_entities:
            return linked_records

        for ext in extracted_entities:
            canonical_name = self.canonicalize_name(ext.text, ext.entity_type)
            aliases = [ext.text.strip()] if ext.text.strip().upper() != canonical_name else []

            if session:
                try:
                    # Upsert canonical entity
                    entity_record = self.entity_repo.upsert_entity(
                        session=session,
                        canonical_name=canonical_name,
                        entity_type=ext.entity_type.value,
                        aliases=aliases,
                        metadata={"last_extracted_text": ext.text},
                    )

                    # Link chunk to entity
                    self.entity_repo.link_chunk_to_entity(
                        session=session,
                        chunk_id=chunk_id,
                        entity_id=entity_record.entity_id,
                        confidence=ext.confidence,
                    )

                    linked_records.append({
                        "chunk_id": chunk_id,
                        "entity_id": entity_record.entity_id,
                        "canonical_name": canonical_name,
                        "entity_type": ext.entity_type.value,
                    })
                except Exception as e:
                    logger.error(f"Failed to link entity {canonical_name} to chunk {chunk_id}: {e}")
            else:
                # In-memory return tracking
                linked_records.append({
                    "chunk_id": chunk_id,
                    "entity_id": f"ent_{canonical_name.lower().replace(' ', '_')}",
                    "canonical_name": canonical_name,
                    "entity_type": ext.entity_type.value,
                })

        logger.info(f"Linked {len(linked_records)} entity occurrences for chunk {chunk_id}.")
        return linked_records

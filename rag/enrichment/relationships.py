"""
Relationship extractor for mapping cross-references between SOPs, technical manuals, and equipment units.
"""

from enum import Enum
import logging
import re
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session

from rag.storage.repositories.entity_repo import EntityRepository

logger = logging.getLogger(__name__)



class RelationshipType(str, Enum):
    REFERENCES = "REFERENCES"
    SUPERSEDES = "SUPERSEDES"
    PARENT_OF = "PARENT_OF"
    BELONGS_TO_UNIT = "BELONGS_TO_UNIT"
    DEPENDS_ON = "DEPENDS_ON"


class DocumentRelationship(BaseModel):
    source_doc_id: str
    target_doc_id: str
    relationship_type: RelationshipType
    description: str = ""
    confidence: float = 1.0


class RelationshipExtractor:
    """Extracts explicit relationships and document cross-references from document text."""

    def __init__(self, entity_repo: Optional[EntityRepository] = None):
        self._ref_pattern = re.compile(r"(?i)(refer\s+to|see|in\s+accordance\s+with|supersedes)\s+([A-Z0-9\-_/]+)")
        self.entity_repo = entity_repo or EntityRepository()

    def extract_relationships(
        self,
        source_doc_id: str,
        text: str,
        session: Optional[Session] = None,
    ) -> List[DocumentRelationship]:
        """Parse text for inter-document references and optionally persist relationships in DB."""
        relationships: List[DocumentRelationship] = []

        for match in self._ref_pattern.finditer(text):
            action_phrase = match.group(1).lower()
            target_id = match.group(2).strip()

            rel_type = RelationshipType.REFERENCES
            if "supersede" in action_phrase:
                rel_type = RelationshipType.SUPERSEDES

            rel = DocumentRelationship(
                source_doc_id=source_doc_id,
                target_doc_id=target_id,
                relationship_type=rel_type,
                description=f"{action_phrase} {target_id}",
                confidence=0.9,
            )
            relationships.append(rel)

            if session:
                try:
                    # Upsert source & target entity nodes for doc relationships
                    source_ent = self.entity_repo.upsert_entity(
                        session=session,
                        canonical_name=source_doc_id,
                        entity_type="SOP_CODE",
                    )
                    target_ent = self.entity_repo.upsert_entity(
                        session=session,
                        canonical_name=target_id,
                        entity_type="SOP_CODE",
                    )
                    self.entity_repo.add_relationship(
                        session=session,
                        source_entity_id=source_ent.entity_id,
                        target_entity_id=target_ent.entity_id,
                        relationship_type=rel_type.value,
                        confidence=rel.confidence,
                        source_document_id=source_doc_id,
                    )
                except Exception as e:
                    logger.warning(f"Could not persist relationship {source_doc_id}->{target_id} in DB: {e}")

        return relationships


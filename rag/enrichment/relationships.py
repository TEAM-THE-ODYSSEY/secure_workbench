"""
Relationship extractor for mapping cross-references between SOPs, technical manuals, and equipment units.
"""

from enum import Enum
import logging
import re
from typing import List, Optional
from pydantic import BaseModel

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

    def __init__(self):
        self._ref_pattern = re.compile(r"(?i)(refer\s+to|see|in\s+accordance\s+with|supersedes)\s+([A-Z0-9\-_/]+)")

    def extract_relationships(self, source_doc_id: str, text: str) -> List[DocumentRelationship]:
        """Parse text for inter-document references."""
        relationships: List[DocumentRelationship] = []

        for match in self._ref_pattern.finditer(text):
            action_phrase = match.group(1).lower()
            target_id = match.group(2).strip()

            rel_type = RelationshipType.REFERENCES
            if "supersede" in action_phrase:
                rel_type = RelationshipType.SUPERSEDES

            relationships.append(
                DocumentRelationship(
                    source_doc_id=source_doc_id,
                    target_doc_id=target_id,
                    relationship_type=rel_type,
                    description=f"{action_phrase} {target_id}",
                    confidence=0.9,
                )
            )

        return relationships

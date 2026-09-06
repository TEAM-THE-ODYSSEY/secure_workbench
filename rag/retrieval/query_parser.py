"""
Query parser for analyzing user queries, extracting intent, technical entities, and implicit metadata filter hints.
"""

import logging
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from rag.enrichment.entity_extractor import EntityExtractor, ExtractedEntity

logger = logging.getLogger(__name__)


class ParsedQuery(BaseModel):
    """Parsed representation of a user query."""
    raw_query: str
    clean_query: str
    extracted_entities: List[ExtractedEntity] = Field(default_factory=list)
    inferred_filters: Dict[str, Any] = Field(default_factory=dict)
    keywords: List[str] = Field(default_factory=list)
    intent: str = "INFORMATIONAL"  # INFORMATIONAL, PROCEDURAL, INCIDENT, TROUBLESHOOTING


class QueryParser:
    """Parses incoming query text to extract intent, entities, and filter conditions."""

    def __init__(self, entity_extractor: Optional[EntityExtractor] = None):
        self.entity_extractor = entity_extractor or EntityExtractor()

    def parse(self, query: str) -> ParsedQuery:
        """Parse raw query string."""
        clean_q = re.sub(r"\s+", " ", query.strip())
        entities = self.entity_extractor.extract_entities(clean_q)

        inferred_filters: Dict[str, Any] = {}
        for ent in entities:
            if ent.entity_type == "EQUIPMENT":
                inferred_filters["equipment_id"] = ent.normalized_name
            elif ent.entity_type == "UNIT":
                inferred_filters["unit"] = ent.normalized_name
            elif ent.entity_type == "SOP_CODE":
                inferred_filters["document_type"] = "SOP"

        # Determine intent
        q_lower = clean_q.lower()
        intent = "INFORMATIONAL"
        if any(w in q_lower for w in ["how to", "procedure", "steps", "operating instructions", "sop"]):
            intent = "PROCEDURAL"
        elif any(w in q_lower for w in ["failure", "trip", "leak", "fire", "incident", "alarm"]):
            intent = "TROUBLESHOOTING"

        # Extract search keywords (alphanumeric terms)
        keywords = [w for w in re.findall(r"\b[A-Za-z0-9\-]+\b", clean_q) if len(w) > 2]

        return ParsedQuery(
            raw_query=query,
            clean_query=clean_q,
            extracted_entities=entities,
            inferred_filters=inferred_filters,
            keywords=keywords,
            intent=intent,
        )

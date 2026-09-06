"""
Entity extractor for identifying MRPL technical domain entities (Equipment IDs, Units, Departments, Processes).
"""

from enum import Enum
import logging
import re
from typing import Dict, List, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class EntityType(str, Enum):
    EQUIPMENT = "EQUIPMENT"
    UNIT = "UNIT"
    DEPARTMENT = "DEPARTMENT"
    PROCESS = "PROCESS"
    SOP_CODE = "SOP_CODE"
    CHEMICAL = "CHEMICAL"
    INCIDENT_CODE = "INCIDENT_CODE"


class ExtractedEntity(BaseModel):
    entity_id: str
    entity_type: EntityType
    text: str
    normalized_name: str
    confidence: float = 1.0
    start_char: int = 0
    end_char: int = 0


class EntityExtractor:
    """Extracts technical entities from document text using pattern matching rules."""

    def __init__(self):
        # Patterns for MRPL refinery terminology
        self._patterns: Dict[EntityType, List[re.Pattern]] = {
            EntityType.EQUIPMENT: [
                re.compile(r"\b([P|K|C|E|V|T|F|B]-\d{3,4}[A-Z]?)\b"),  # e.g. P-101A, K-201, C-301
                re.compile(r"\b(EQUIPMENT|TAG)\s*#?\s*([A-Z0-9\-]+)\b", re.IGNORECASE),
            ],
            EntityType.UNIT: [
                re.compile(r"\b(CDU|VDU|DHDS|HCU|CCR|FCCU|PFCC|DCU|NHT|ISOM|ARU|SWS)\b", re.IGNORECASE),
                re.compile(r"\bUNIT\s*-\s*(\d+|[A-Z0-9]+)\b", re.IGNORECASE),
            ],
            EntityType.SOP_CODE: [
                re.compile(r"\b(SOP-[A-Z0-9\-]+)\b", re.IGNORECASE),
                re.compile(r"\b(DOC-[A-Z0-9\-]+)\b", re.IGNORECASE),
            ],
            EntityType.CHEMICAL: [
                re.compile(r"\b(Crude Oil|Naphtha|Kerosene|Diesel|LPG|Furnace Oil|Bitumen|Sulphur|Hydrogen)\b", re.IGNORECASE),
            ],
        }

    def extract_entities(self, text: str) -> List[ExtractedEntity]:
        """Extract entities from input text."""
        entities: List[ExtractedEntity] = []
        counter = 0

        for ent_type, patterns in self._patterns.items():
            for pat in patterns:
                for match in pat.finditer(text):
                    counter += 1
                    matched_str = match.group(0)
                    norm_str = matched_str.upper()
                    entities.append(
                        ExtractedEntity(
                            entity_id=f"ent_{ent_type.value.lower()}_{counter}",
                            entity_type=ent_type,
                            text=matched_str,
                            normalized_name=norm_str,
                            confidence=0.95,
                            start_char=match.start(),
                            end_char=match.end(),
                        )
                    )

        return entities

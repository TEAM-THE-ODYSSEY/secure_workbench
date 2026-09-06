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
    """Extracts technical entities from document text using pattern matching rules and optional spaCy NER."""

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
        self._nlp = None
        self._load_spacy()

    def _load_spacy(self):
        """Lazy try-load spaCy model for general entity extraction."""
        try:
            import spacy
            try:
                self._nlp = spacy.load("en_core_web_sm")
                logger.info("Loaded spaCy en_core_web_sm model for entity extraction.")
            except Exception:
                logger.warning("spaCy installed but en_core_web_sm model missing. Using regex entity extraction.")
        except ImportError:
            logger.debug("spaCy not installed. Using regex entity extraction.")

    def extract_entities(self, text: str) -> List[ExtractedEntity]:
        """Extract entities from input text using regex rules and spaCy."""
        entities: List[ExtractedEntity] = []
        counter = 0
        seen_spans = set()

        # 1. Regex rule extraction (highest priority for refinery technical codes)
        for ent_type, patterns in self._patterns.items():
            for pat in patterns:
                for match in pat.finditer(text):
                    counter += 1
                    matched_str = match.group(0)
                    norm_str = matched_str.upper()
                    span = (match.start(), match.end())
                    seen_spans.add(span)

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

        # 2. spaCy NER extraction for departments/organizations if available
        if self._nlp:
            try:
                doc = self._nlp(text)
                for ent in doc.ents:
                    span = (ent.start_char, ent.end_char)
                    if span in seen_spans or len(ent.text.strip()) < 2:
                        continue
                    
                    ent_type = None
                    if ent.label_ == "ORG":
                        ent_type = EntityType.DEPARTMENT
                    elif ent.label_ in ("PRODUCT", "LAW"):
                        ent_type = EntityType.PROCESS

                    if ent_type:
                        counter += 1
                        entities.append(
                            ExtractedEntity(
                                entity_id=f"ent_{ent_type.value.lower()}_{counter}",
                                entity_type=ent_type,
                                text=ent.text,
                                normalized_name=ent.text.strip().upper(),
                                confidence=0.8,
                                start_char=ent.start_char,
                                end_char=ent.end_char,
                            )
                        )
            except Exception as e:
                logger.warning(f"spaCy entity extraction error: {e}")

        return entities


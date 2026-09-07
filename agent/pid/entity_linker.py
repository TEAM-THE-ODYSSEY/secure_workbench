"""
P&ID Engineering Tag Canonical Entity Linker.
Resolves engineering tag variations (e.g. P-101A, P 101 A, Pump P101A, Pump-P101A)
to canonical entity records (e.g. EQ-P101A) in the centralized PostgreSQL database.
"""

import re
import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from rag.storage.postgres import db_manager, EntityModel
from rag.storage.repositories.entity_repo import EntityRepository
from agent.pid.schemas import PIDEntity

logger = logging.getLogger("agent.pid.entity_linker")


class PIDEntityLinker:
    """
    Canonical entity linker linking P&ID engineering tags to centralized PostgreSQL EntityModel.
    """

    TAG_PREFIX_PATTERNS = {
        r"^P[-_\s]?\d{3}[A-Z]?": ("PUMP", "EQ-P"),
        r"^V[-_\s]?\d{3}[A-Z]?": ("VESSEL", "EQ-V"),
        r"^XV[-_\s]?\d{3}[A-Z]?": ("VALVE", "V-XV"),
        r"^HV[-_\s]?\d{3}[A-Z]?": ("VALVE", "V-HV"),
        r"^CV[-_\s]?\d{3}[A-Z]?": ("VALVE", "V-CV"),
        r"^PT[-_\s]?\d{3}[A-Z]?": ("INSTRUMENT", "INS-PT"),
        r"^FT[-_\s]?\d{3}[A-Z]?": ("INSTRUMENT", "INS-FT"),
        r"^TT[-_\s]?\d{3}[A-Z]?": ("INSTRUMENT", "INS-TT"),
        r"^PIC[-_\s]?\d{3}[A-Z]?": ("INSTRUMENT", "INS-PIC"),
        r"^H[-_\s]?\d{3}[A-Z]?": ("HEATER", "EQ-H"),
    }

    def __init__(self, entity_repo: Optional[EntityRepository] = None):
        self.entity_repo = entity_repo or EntityRepository()

    def canonicalize_tag(self, raw_tag: str) -> str:
        """
        Normalize variations like 'P 101 A' or 'Pump-P101A' to canonical 'P-101A'.
        """
        tag = raw_tag.strip().upper()
        # Remove words like PUMP, VALVE, INSTRUMENT
        tag = re.sub(r"^(PUMP|VALVE|INSTRUMENT|VESSEL|HEATER)\s*", "", tag)
        tag = re.sub(r"\s+", "", tag)

        # Standardize hyphens: e.g. P101A -> P-101A
        match = re.match(r"^([A-Z]+)[-_\s]?(\d+[A-Z]?)$", tag)
        if match:
            prefix, num = match.groups()
            return f"{prefix}-{num}"

        return tag

    def get_canonical_entity_id(self, tag: str) -> str:
        """Generate deterministic canonical entity ID from normalized tag."""
        norm_tag = self.canonicalize_tag(tag)
        clean_id = norm_tag.replace("-", "").replace("_", "")
        return f"EQ-{clean_id}"

    def infer_type_from_tag(self, tag: str) -> str:
        """Infer equipment type (PUMP, VALVE, INSTRUMENT, VESSEL, HEATER) from tag prefix."""
        norm_tag = self.canonicalize_tag(tag)
        for pattern, (eq_type, _) in self.TAG_PREFIX_PATTERNS.items():
            if re.match(pattern, norm_tag):
                return eq_type
        if norm_tag.startswith("P-"):
            return "PUMP"
        elif norm_tag.startswith("XV-") or norm_tag.startswith("HV-") or norm_tag.startswith("CV-") or norm_tag.startswith("V-"):
            return "VALVE"
        elif norm_tag.startswith("PT-") or norm_tag.startswith("FT-") or norm_tag.startswith("PIC-"):
            return "INSTRUMENT"
        elif norm_tag.startswith("H-"):
            return "HEATER"
        return "EQUIPMENT"

    def resolve_entity(self, raw_tag: str, session: Optional[Session] = None) -> PIDEntity:
        """
        Resolve raw tag to a PIDEntity linked with PostgreSQL EntityModel.
        """
        norm_tag = self.canonicalize_tag(raw_tag)
        canonical_id = self.get_canonical_entity_id(norm_tag)
        eq_type = self.infer_type_from_tag(norm_tag)

        own_session = False
        if not session:
            try:
                session = db_manager.get_session()
                own_session = True
            except Exception as e:
                logger.warning(f"DB session unavailable for tag '{norm_tag}': {e}")
                session = None

        if session:
            try:
                # Upsert into PostgreSQL canonical EntityModel
                self.entity_repo.upsert_entity(
                    session=session,
                    canonical_name=canonical_id,
                    entity_type=eq_type,
                    aliases=[raw_tag, norm_tag],
                    metadata={"tag": norm_tag, "domain": "P&ID"},
                )
                if own_session:
                    session.commit()
            except Exception as e:
                logger.warning(f"DB entity upsert failed for tag '{norm_tag}': {e}")
                if own_session:
                    session.rollback()
            finally:
                if own_session:
                    session.close()

        return PIDEntity(
            id=canonical_id,
            type=eq_type,
            tag=norm_tag,
            confidence=1.0,
        )

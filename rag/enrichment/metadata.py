"""
Metadata schemas and enrichment logic for MRPL technical documents and SOPs.
"""

from datetime import datetime
import logging
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DocumentMetadata(BaseModel):
    """Enterprise metadata schema for MRPL documents."""
    document_id: str
    title: str = "Untitled Document"
    document_type: str = "SOP"  # SOP, Manual, Technical Spec, Log, Incident Report
    department: str = "Operations"  # Operations, Maintenance, HSE, Inspection, Engineering
    plant: str = "MRPL Refinery"  # Refinery, Petrochemical, Jetty, Offsites
    unit: str = "CDU-1"  # CDU-1, VDU-1, DHDS, HCU, CCR, FCCU
    equipment_id: str = "UNSPECIFIED"  # e.g., P-101A, K-201, C-301
    equipment_type: str = "UNSPECIFIED"  # Pump, Compressor, Column, Heat Exchanger, Valve
    section: str = "General"
    page_number: int = 1
    revision: str = "R0"
    effective_date: Optional[str] = None
    expiry_date: Optional[str] = None
    status: str = "ACTIVE"  # ACTIVE, SUPERSEDED, DRAFT, ARCHIVED
    source: str = "Internal"
    access_level: str = "PUBLIC"  # PUBLIC, RESTRICTED, CONFIDENTIAL
    language: str = "en"
    extra_attributes: Dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata instance to a flattened dictionary suitable for filtering."""
        data = self.model_dump()
        extra = data.pop("extra_attributes", {})
        data.update(extra)
        return data


class MetadataEnricher:
    """Enriches raw document metadata with inferred attributes from filename or content patterns."""

    def __init__(self, default_department: str = "Operations", default_plant: str = "MRPL Refinery"):
        self.default_department = default_department
        self.default_plant = default_plant

    def enrich(self, raw_metadata: Dict[str, Any], doc_title: str, full_text: str) -> DocumentMetadata:
        """Derive and build complete DocumentMetadata object."""
        doc_id = raw_metadata.get("document_id") or raw_metadata.get("absolute_path") or f"doc_{hash(doc_title)}"
        
        # Infer equipment/unit from text if present
        unit = raw_metadata.get("unit", "CDU-1")
        equipment_id = raw_metadata.get("equipment_id", "UNSPECIFIED")
        
        # Simple rule-based inference from document title or text
        title_lower = doc_title.lower()
        doc_type = raw_metadata.get("document_type", "SOP")
        if "manual" in title_lower:
            doc_type = "Manual"
        elif "spec" in title_lower or "specification" in title_lower:
            doc_type = "Technical Spec"
        elif "report" in title_lower or "incident" in title_lower:
            doc_type = "Incident Report"

        return DocumentMetadata(
            document_id=str(doc_id),
            title=raw_metadata.get("title") or doc_title,
            document_type=doc_type,
            department=raw_metadata.get("department", self.default_department),
            plant=raw_metadata.get("plant", self.default_plant),
            unit=unit,
            equipment_id=equipment_id,
            equipment_type=raw_metadata.get("equipment_type", "UNSPECIFIED"),
            section=raw_metadata.get("section", "General"),
            page_number=int(raw_metadata.get("page_number", 1)),
            revision=raw_metadata.get("revision", "R0"),
            effective_date=raw_metadata.get("effective_date", datetime.utcnow().strftime("%Y-%m-%d")),
            expiry_date=raw_metadata.get("expiry_date"),
            status=raw_metadata.get("status", "ACTIVE"),
            source=raw_metadata.get("source", "Internal File System"),
            access_level=raw_metadata.get("access_level", "RESTRICTED"),
            language=raw_metadata.get("language", "en"),
            extra_attributes=raw_metadata,
        )

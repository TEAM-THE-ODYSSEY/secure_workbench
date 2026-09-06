"""
Data models for P&ID knowledge representation, entities, connections, and provenance.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PIDSourceProvenance(BaseModel):
    """Provenance tracking for P&ID extracted evidence."""
    document_id: str
    version_id: str = "1.0"
    page: int = 1
    title: Optional[str] = None


class PIDEntity(BaseModel):
    """P&ID extracted equipment, valve, or instrument entity."""
    id: str = Field(..., description="Canonical entity ID e.g. EQ-P101A")
    type: str = Field(..., description="Entity type: PUMP, VALVE, INSTRUMENT, VESSEL, HEATER")
    tag: str = Field(..., description="Engineering tag e.g. P-101A, XV-101, PT-101")
    confidence: float = Field(default=1.0, description="Detection/linking confidence score")


class PIDConnection(BaseModel):
    """Directed connection between two P&ID entities."""
    source_entity: str = Field(..., alias="from", description="Source canonical entity ID e.g. EQ-P101A")
    target_entity: str = Field(..., alias="to", description="Target canonical entity ID e.g. V-XV101")
    relationship: str = Field(default="DOWNSTREAM", description="Relationship type: DOWNSTREAM, UPSTREAM, MONITORED_BY, ISOLATED_BY")
    pipe: Optional[str] = Field(default=None, description="Piping line identifier e.g. 4-CR-101-CS")
    confidence: float = Field(default=1.0, description="Topology confidence")
    provenance: Optional[PIDSourceProvenance] = None

    class Config:
        populate_by_name = True


class PIDDiagramKnowledge(BaseModel):
    """Structured P&ID diagram representation according to MRPL system standard."""
    diagram_id: str
    page: int = 1
    entities: List[PIDEntity] = Field(default_factory=list)
    connections: List[PIDConnection] = Field(default_factory=list)
    source: PIDSourceProvenance
    warnings: List[str] = Field(default_factory=list)

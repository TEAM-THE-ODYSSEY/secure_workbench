from __future__ import annotations
from typing import Any, Dict, List, Tuple
from pydantic import BaseModel, Field

Point = Tuple[float, float]
BBox = Tuple[float, float, float, float]

class SymbolDetection(BaseModel):
    object_id: str
    object_type: str
    bbox: BBox
    confidence: float = 0.0

class OCRText(BaseModel):
    text: str
    bbox: BBox
    confidence: float = 0.0

class LineDetection(BaseModel):
    line_id: str
    points: List[Point]
    line_type: str = "unknown"
    confidence: float = 0.0

class FusedObject(BaseModel):
    object_id: str
    object_type: str
    tag: str | None = None
    bbox: BBox
    symbol_confidence: float = 0.0
    ocr_confidence: float = 0.0
    association_confidence: float = 0.0
    evidence: List[str] = Field(default_factory=list)

class Relationship(BaseModel):
    source: str
    target: str
    relationship: str
    pipe: str | None = None
    confidence: float = 0.0
    evidence: List[str] = Field(default_factory=list)

class PIDAnalysisResult(BaseModel):
    objects: List[FusedObject] = Field(default_factory=list)
    lines: List[LineDetection] = Field(default_factory=list)
    relationships: List[Relationship] = Field(default_factory=list)
    graph: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)

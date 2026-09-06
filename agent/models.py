"""
Pydantic v2 data models for the Reasoning Mini-Agent V1.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TaskRequest(BaseModel):
    """Input payload for a reasoning task."""
    task_type: str = Field(default="GENERATE_PDF", description="Task type (e.g. GENERATE_PDF)")
    objective: str = Field(..., description="Natural language objective or user request")
    entities: List[str] = Field(default_factory=list, description="Target entity IDs/names e.g. EQ-P101A")
    document_type: Optional[str] = Field(default=None, description="Optional document type filter")
    version_constraint: Optional[str] = Field(default=None, description="Optional version constraint")


class Citation(BaseModel):
    """Source reference mapping claims to evidence."""
    document_id: str
    title: str
    version: str = "1.0"
    section: Optional[str] = None
    page: Optional[int] = None
    trust_level: str = "TRUSTED"
    snippet: Optional[str] = None


class EvidenceChunk(BaseModel):
    """Structured evidence item returned by Knowledge Tool."""
    document_id: str
    title: str
    version: str
    section: str
    page: Optional[int] = None
    entity_id: Optional[str] = None
    trust_level: str = "TRUSTED"
    content: str
    citation: Citation


class ProcedureStep(BaseModel):
    """Numbered procedural instruction."""
    step_number: int
    instruction: str
    citations: List[Citation] = Field(default_factory=list)


class OperatingLimit(BaseModel):
    """Equipment or operational boundary parameters."""
    parameter: str
    value: str
    citations: List[Citation] = Field(default_factory=list)


class StructuredPDFContent(BaseModel):
    """Strict schema for reasoning LLM output before PDF generation."""
    title: str
    purpose: str
    scope: str
    preconditions: List[str] = Field(default_factory=list)
    safety_requirements: List[str] = Field(default_factory=list)
    procedure_steps: List[ProcedureStep] = Field(default_factory=list)
    operating_limits: List[OperatingLimit] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    references: List[Citation] = Field(default_factory=list)


class ArtifactMetadata(BaseModel):
    """MinIO persistent artifact reference metadata."""
    filename: str
    content_type: str = "application/pdf"
    storage_uri: Optional[str] = None
    file_size_bytes: int = 0
    bucket: Optional[str] = None


class AgentTaskResult(BaseModel):
    """Final API response schema for POST /api/v1/agent/reason."""
    task_id: str
    status: str  # COMPLETED, INSUFFICIENT_EVIDENCE, VERIFICATION_FAILED, PDF_GENERATION_FAILED, TOOL_ERROR, MODEL_ERROR
    result_type: str = "PDF"
    artifact: Optional[ArtifactMetadata] = None
    model: str
    fallback_used: bool = False
    citations: List[Citation] = Field(default_factory=list)
    message: Optional[str] = None
    structured_content: Optional[StructuredPDFContent] = None

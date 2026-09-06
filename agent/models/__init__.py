"""
Models package for Main AI Agent.
Exposes domain Pydantic schemas, vLLM client, and ModelManager abstraction.
"""

from agent.models.schemas import (
    TaskRequest,
    AgentTaskResult,
    StructuredPDFContent,
    EvidenceChunk,
    Citation,
    ProcedureStep,
    OperatingLimit,
    ArtifactMetadata,
    ExecutionTraceRecord,
    ContextPlan,
    FinalReasoningOutput,
)
from agent.models.vllm_client import VLLMClient
from agent.models.model_manager import ModelManager, InfrastructureError, QualityFailureError

__all__ = [
    "TaskRequest",
    "AgentTaskResult",
    "StructuredPDFContent",
    "EvidenceChunk",
    "Citation",
    "ProcedureStep",
    "OperatingLimit",
    "ArtifactMetadata",
    "ExecutionTraceRecord",
    "ContextPlan",
    "FinalReasoningOutput",
    "VLLMClient",
    "ModelManager",
    "InfrastructureError",
    "QualityFailureError",
]

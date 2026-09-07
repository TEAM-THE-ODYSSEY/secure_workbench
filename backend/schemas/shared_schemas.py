from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Optional, Union
from pydantic import BaseModel

TaskStatus = Literal["CREATED", "PLANNING", "RUNNING", "WAITING",
                      "VERIFYING", "COMPLETED", "FAILED"]
TaskType = Literal["SIMPLE", "REASONING", "CODING", "MATHEMATICAL",
                    "DOCUMENT", "MULTIMODAL"]
AgentName = Literal["normal_llm", "reasoning_agent", "coding_agent",
                     "mathematical_agent"]
ToolName = Literal["ocr", "vision", "knowledge", "file_read",
                    "file_write", "python_execution"]
ModelId = Literal["general_model", "reasoning_model", "coding_model",
                   "vision_model", "embedding_model"]
ArtifactType = Literal["docx", "xlsx", "pptx", "pdf", "txt", "csv"]

class Source(BaseModel):
    document_name: str
    page: Optional[int] = None
    section: Optional[str] = None
    retrieved_text: str
    relevance_score: float

class Artifact(BaseModel):
    artifact_id: str
    file_name: str
    file_type: ArtifactType
    download_url: Optional[str] = None

class Verification(BaseModel):
    verified: bool
    notes: str

class ModelInfo(BaseModel):
    model_id: Union[ModelId, str]
    model_name: str
    model_type: str
    capabilities: list[str]
    context_length: int
    quantization: str
    memory_requirement: str
    supported_tasks: list[TaskType]
    ollama_tag: Optional[str] = None
    is_default_for_tasks: list[TaskType] = []

class ModelsListResponse(BaseModel):
    models: list[ModelInfo]


class TaskState(BaseModel):
    task_id: str
    user_request: str
    input_files: list[str] = []
    task_type: Optional[TaskType] = None
    selected_model: Optional[Union[ModelId, str]] = None
    current_agent: Optional[AgentName] = None
    plan: Optional[list[str]] = None
    current_step: Optional[int] = None
    tool_calls: list[dict] = []
    tool_results: list[dict] = []
    retrieved_sources: list[Source] = []
    calculations: list[dict] = []
    generated_artifacts: list[Artifact] = []
    errors: list[str] = []
    status: TaskStatus = "CREATED"
    answer: Optional[str] = None
    verification: Optional[Verification] = None
    agent_stack: list[str] = []
    handoff_context: Optional[dict] = None
    model_selection_notes: Optional[str] = None

class TaskCreatedResponse(BaseModel):
    task_id: str
    session_id: str
    status: Literal["CREATED"] = "CREATED"

class TaskFinalResponse(BaseModel):
    task_id: str
    status: Literal["COMPLETED", "FAILED"]
    answer: Optional[str]
    task_type: Optional[TaskType]
    agent: Optional[AgentName]
    model: Optional[Union[ModelId, str]]
    plan: Optional[list[str]]
    tool_calls: list[dict]
    sources: list[Source]
    artifacts: list[Artifact]
    verification: Optional[Verification]
    errors: list[str]
    error: Optional[str]
    model_selection_notes: Optional[str] = None

    @classmethod
    def from_task_state(cls, state: TaskState) -> "TaskFinalResponse":
        return cls(
            task_id=state.task_id, status=state.status, answer=state.answer,
            task_type=state.task_type, agent=state.current_agent,
            model=state.selected_model, plan=state.plan,
            tool_calls=state.tool_calls, sources=state.retrieved_sources,
            artifacts=state.generated_artifacts, verification=state.verification,
            errors=state.errors,
            error=(state.errors[-1] if state.status == "FAILED" and state.errors else None),
            model_selection_notes=state.model_selection_notes,
        )

class WebSocketEvent(BaseModel):
    event: Literal["status_change", "tool_call", "agent_handoff", "final"]
    status: Optional[TaskStatus] = None
    current_agent: Optional[AgentName] = None
    tool: Optional[ToolName] = None
    success: Optional[bool] = None
    summary: Optional[str] = None
    from_agent: Optional[AgentName] = None
    to_agent: Optional[AgentName] = None
    result: Optional[TaskFinalResponse] = None

class HealthResponse(BaseModel):
    status: Literal["ok"]
    local_only: bool
    external_calls_enabled: bool

@dataclass(frozen=True)
class EngineLimits:
    max_iterations: int = 10
    max_tool_calls: int = 15
    max_retries_per_tool: int = 2
    max_execution_time_sec: int = 60

DEFAULT_LIMITS = EngineLimits()

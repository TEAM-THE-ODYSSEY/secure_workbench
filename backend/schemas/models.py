from __future__ import annotations
from pydantic import BaseModel

try:
    from backend.schemas.shared_schemas import TaskType
except ImportError:
    from schemas.shared_schemas import TaskType


class AddModelRequest(BaseModel):
    model_id: str
    model_name: str
    ollama_tag: str                              # exact tag Ollama needs, e.g. "mistral:7b-instruct"
    model_type: str
    capabilities: list[str]
    context_length: int
    quantization: str
    memory_requirement: str
    supported_tasks: list[TaskType]
    is_default_for_tasks: list[TaskType] = []    # admin opt-in: which task types should route to this model

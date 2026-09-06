from __future__ import annotations

from abc import ABC, abstractmethod

from ..schemas.task import Task
from ..schemas.response import AgentResponse
from ..tools.gateway import OllamaGateway


class BaseAgent(ABC):
    """
    Every agent (reasoning, mathematical, and future ones — vision, RAG,
    coding, etc.) implements this interface. The orchestrator only ever
    calls `run(task)`, so new agents can be dropped in without touching
    orchestrator code.
    """

    name: str = "base_agent"

    def __init__(self, gateway: OllamaGateway, model: str | None = None):
        self.gateway = gateway
        self.model = model  # None => gateway.default_model is used

    @abstractmethod
    def run(self, task: Task) -> AgentResponse:
        ...

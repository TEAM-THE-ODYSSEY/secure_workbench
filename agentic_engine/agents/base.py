from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    def __init__(self, llm):
        self.llm = llm

    @abstractmethod
    def run(self, user_text: str, context: str, model: str, metadata: dict[str, Any]) -> str:
        raise NotImplementedError

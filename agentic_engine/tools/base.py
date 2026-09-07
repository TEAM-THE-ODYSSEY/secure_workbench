from __future__ import annotations

import hashlib
import json
import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional


@dataclass
class ToolExecutionRecord:
    tool: str
    input_hash: str
    start_time: float
    end_time: float
    duration: float
    status: str
    output: Any = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BaseTool(ABC):
    """Base class for traceable, policy-governed tools (Section 14 & 15)."""
    name: str = "base_tool"
    description: str = ""

    def __call__(self, **kwargs) -> ToolExecutionRecord:
        return self.run(**kwargs)

    @staticmethod
    def compute_input_hash(data: Any) -> str:
        try:
            serialized = json.dumps(data, sort_keys=True, default=str)
        except Exception:
            serialized = str(data)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]

    def run(self, **kwargs) -> ToolExecutionRecord:
        start_time = time.time()
        input_hash = self.compute_input_hash(kwargs)
        try:
            output = self._execute(**kwargs)
            end_time = time.time()
            return ToolExecutionRecord(
                tool=self.name,
                input_hash=input_hash,
                start_time=start_time,
                end_time=end_time,
                duration=round((end_time - start_time) * 1000, 2),
                status="SUCCESS",
                output=output,
                error=None,
            )
        except Exception as exc:
            end_time = time.time()
            return ToolExecutionRecord(
                tool=self.name,
                input_hash=input_hash,
                start_time=start_time,
                end_time=end_time,
                duration=round((end_time - start_time) * 1000, 2),
                status="FAILED",
                output=None,
                error=str(exc),
            )

    @abstractmethod
    def _execute(self, **kwargs) -> Any:
        raise NotImplementedError

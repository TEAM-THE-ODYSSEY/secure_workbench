from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Span:
    name: str
    start_time: float
    end_time: float = 0.0
    duration_ms: float = 0.0
    status: str = "OK"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def finish(self, status: str = "OK", **meta):
        self.end_time = time.time()
        self.duration_ms = round((self.end_time - self.start_time) * 1000, 2)
        self.status = status
        self.metadata.update(meta)


@dataclass
class ExecutionTrace:
    trace_id: str
    request_id: str
    spans: List[Span] = field(default_factory=list)
    state_transitions: List[Dict[str, str]] = field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    tokens_used: int = 0
    retries: int = 0
    replans: int = 0

    def start_span(self, name: str, **meta) -> Span:
        span = Span(name=name, start_time=time.time(), metadata=meta)
        self.spans.append(span)
        return span

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "request_id": self.request_id,
            "spans": [asdict(s) for s in self.spans],
            "state_transitions": self.state_transitions,
            "tool_calls": self.tool_calls,
            "tokens_used": self.tokens_used,
            "retries": self.retries,
            "replans": self.replans,
        }


class Tracer:
    """Creates and records execution traces."""

    @staticmethod
    def start_trace(request_id: Optional[str] = None) -> ExecutionTrace:
        trace_id = f"trace_{uuid.uuid4().hex[:12]}"
        req_id = request_id or f"req_{uuid.uuid4().hex[:8]}"
        return ExecutionTrace(trace_id=trace_id, request_id=req_id)

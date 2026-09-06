"""
Execution Trace Tracker for recording safe audit trails, active model, fallback status,
and performance latency breakdowns across Main Agent phases.
"""

import time
import logging
from typing import Any, Dict, List, Optional
from agent.models.schemas import ExecutionTraceRecord

logger = logging.getLogger("agent.execution_trace")


class ExecutionTraceTracker:
    """
    Tracks state machine execution trace and latency breakdown for Main AI Agent.
    """

    def __init__(self, task_id: str):
        self.task_id = task_id
        self.start_time = time.time()
        self.intent = "UNKNOWN"
        self.entities: List[str] = []
        self.tools_called: List[str] = []
        self.evidence_count = 0
        self.active_model = "Qwen3-4B"
        self.fallback_used = False
        self.verification_status = "PASSED"
        self.latency_breakdown: Dict[str, float] = {}

    def record_phase(self, phase_name: str, duration_ms: float):
        """Record duration of execution phase in milliseconds."""
        self.latency_breakdown[phase_name] = round(duration_ms, 2)

    def log_tool_call(self, tool_name: str):
        """Log tool invocation."""
        if tool_name not in self.tools_called:
            self.tools_called.append(tool_name)

    def get_record(self) -> ExecutionTraceRecord:
        """Compile and return ExecutionTraceRecord."""
        total_latency = round((time.time() - self.start_time) * 1000, 2)
        return ExecutionTraceRecord(
            task_id=self.task_id,
            intent=self.intent,
            entities=self.entities,
            tools_called=self.tools_called,
            evidence_count=self.evidence_count,
            active_model=self.active_model,
            fallback_used=self.fallback_used,
            verification=self.verification_status,
            latency_ms=total_latency,
            latency_breakdown=self.latency_breakdown,
        )

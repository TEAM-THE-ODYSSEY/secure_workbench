from __future__ import annotations

import time
from dataclasses import dataclass


class BudgetExceededError(RuntimeError):
    """Raised when an execution exceeds its allocated token, call, or time budget."""
    pass


@dataclass
class ExecutionBudget:
    max_tokens: int = 4096
    max_iterations: int = 3
    max_retries: int = 2
    max_tool_calls: int = 6
    max_latency_seconds: float = 90.0
    max_context_chars: int = 32768

    @classmethod
    def for_complexity(cls, complexity: str) -> ExecutionBudget:
        c = (complexity or "medium").lower()
        if c == "small":
            return cls(
                max_tokens=1024,
                max_iterations=1,
                max_retries=1,
                max_tool_calls=1,
                max_latency_seconds=30.0,
                max_context_chars=4096,
            )
        elif c == "large":
            return cls(
                max_tokens=8192,
                max_iterations=3,
                max_retries=3,
                max_tool_calls=12,
                max_latency_seconds=180.0,
                max_context_chars=65536,
            )
        else:
            return cls(
                max_tokens=4096,
                max_iterations=3,
                max_retries=3,
                max_tool_calls=8,
                max_latency_seconds=90.0,
                max_context_chars=16384,
            )


class BudgetTracker:
    """Tracks consumption and raises BudgetExceededError if limits are breached."""

    def __init__(self, budget: ExecutionBudget):
        self.budget = budget
        self.start_time = time.time()
        self.tokens_used = 0
        self.iterations_used = 0
        self.retries_used = 0
        self.tool_calls_used = 0

    def record_tool_call(self) -> None:
        self.tool_calls_used += 1
        if self.tool_calls_used > self.budget.max_tool_calls:
            raise BudgetExceededError(
                f"BUDGET_EXCEEDED: Maximum tool calls ({self.budget.max_tool_calls}) reached."
            )

    def record_iteration(self) -> None:
        self.iterations_used += 1
        if self.iterations_used > self.budget.max_iterations:
            raise BudgetExceededError(
                f"BUDGET_EXCEEDED: Maximum iterations ({self.budget.max_iterations}) reached."
            )

    def record_retry(self) -> None:
        self.retries_used += 1
        if self.retries_used > self.budget.max_retries:
            raise BudgetExceededError(
                f"BUDGET_EXCEEDED: Maximum retries ({self.budget.max_retries}) reached."
            )

    def check_timeout(self) -> None:
        elapsed = time.time() - self.start_time
        if elapsed > self.budget.max_latency_seconds:
            raise BudgetExceededError(
                f"BUDGET_EXCEEDED: Execution timed out after {elapsed:.1f}s (Budget: {self.budget.max_latency_seconds}s)."
            )

    def elapsed_seconds(self) -> float:
        return time.time() - self.start_time

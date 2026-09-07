from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional, Set


class ExecutionState(str, Enum):
    CREATED = "CREATED"
    PLANNED = "PLANNED"
    AUTHORIZED = "AUTHORIZED"
    MODEL_SELECTED = "MODEL_SELECTED"
    RUNNING = "RUNNING"
    TOOL_EXECUTION = "TOOL_EXECUTION"
    VALIDATING = "VALIDATING"
    REPAIRING = "REPAIRING"
    REPLANNING = "REPLANNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"


# Valid state transitions graph
VALID_TRANSITIONS: Dict[ExecutionState, Set[ExecutionState]] = {
    ExecutionState.CREATED: {ExecutionState.PLANNED, ExecutionState.BLOCKED, ExecutionState.CANCELLED, ExecutionState.FAILED},
    ExecutionState.PLANNED: {ExecutionState.AUTHORIZED, ExecutionState.BLOCKED, ExecutionState.FAILED, ExecutionState.CANCELLED},
    ExecutionState.AUTHORIZED: {ExecutionState.MODEL_SELECTED, ExecutionState.BLOCKED, ExecutionState.FAILED, ExecutionState.CANCELLED},
    ExecutionState.MODEL_SELECTED: {ExecutionState.RUNNING, ExecutionState.FAILED, ExecutionState.CANCELLED, ExecutionState.REPLANNING},
    ExecutionState.RUNNING: {ExecutionState.TOOL_EXECUTION, ExecutionState.VALIDATING, ExecutionState.FAILED, ExecutionState.TIMEOUT, ExecutionState.CANCELLED},
    ExecutionState.TOOL_EXECUTION: {ExecutionState.RUNNING, ExecutionState.VALIDATING, ExecutionState.FAILED, ExecutionState.TIMEOUT, ExecutionState.CANCELLED},
    ExecutionState.VALIDATING: {ExecutionState.COMPLETED, ExecutionState.REPAIRING, ExecutionState.REPLANNING, ExecutionState.FAILED},
    ExecutionState.REPAIRING: {ExecutionState.RUNNING, ExecutionState.VALIDATING, ExecutionState.FAILED, ExecutionState.TIMEOUT},
    ExecutionState.REPLANNING: {ExecutionState.PLANNED, ExecutionState.FAILED, ExecutionState.CANCELLED},
    ExecutionState.COMPLETED: set(),
    ExecutionState.FAILED: set(),
    ExecutionState.BLOCKED: set(),
    ExecutionState.TIMEOUT: set(),
    ExecutionState.CANCELLED: set(),
}


class InvalidStateTransitionError(RuntimeError):
    pass


class StateTracker:
    """Tracks state history and strictly enforces state transition rules."""

    def __init__(self, initial_state: ExecutionState = ExecutionState.CREATED):
        self._current_state: ExecutionState = initial_state
        self._history: List[Dict[str, str]] = [{"state": initial_state.value, "reason": "initialization"}]

    @property
    def current(self) -> ExecutionState:
        return self._current_state

    def transition_to(self, new_state: ExecutionState, reason: str = "") -> None:
        valid_next = VALID_TRANSITIONS.get(self._current_state, set())
        if new_state not in valid_next and new_state != self._current_state:
            raise InvalidStateTransitionError(
                f"Illegal state transition: Cannot transition from {self._current_state.value} to {new_state.value}."
            )
        self._current_state = new_state
        self._history.append({"state": new_state.value, "reason": reason})

    def history(self) -> List[Dict[str, str]]:
        return list(self._history)

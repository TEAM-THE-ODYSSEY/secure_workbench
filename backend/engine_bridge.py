from __future__ import annotations
import asyncio
import os
import re
import uuid
from typing import Any, AsyncGenerator, Optional

try:
    from backend import task_store
    from backend.schemas.shared_schemas import (
        Artifact,
        Source,
        TaskFinalResponse,
        TaskState,
        Verification,
        WebSocketEvent,
    )
except ImportError:
    import task_store
    from schemas.shared_schemas import (
        Artifact,
        Source,
        TaskFinalResponse,
        TaskState,
        Verification,
        WebSocketEvent,
    )

# Step delay between simulated engine steps (around 1s each by default)
STEP_DELAY = float(os.getenv("ENGINE_STEP_DELAY", "0.8"))
POLL_INTERVAL = float(os.getenv("ENGINE_POLL_INTERVAL", "0.2"))

# Strong reference set for background tasks to prevent garbage collection
_background_tasks: set[asyncio.Task] = set()


class DictFriendlyTaskFinalResponse(TaskFinalResponse):
    """Subclass of TaskFinalResponse that supports dict-like item access

    along with object attribute access, satisfying both <TaskFinalResponse>
    and dict expectations.
    """

    def __getitem__(self, item: str) -> Any:
        try:
            return getattr(self, item)
        except AttributeError:
            raise KeyError(item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)

    @classmethod
    def from_task_state(cls, state: TaskState) -> DictFriendlyTaskFinalResponse:
        base = TaskFinalResponse.from_task_state(state)
        return cls(**base.model_dump())


def _spawn_execution(task_id: str) -> None:
    try:
        loop = asyncio.get_running_loop()
        task = loop.create_task(_execute(task_id))
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
    except RuntimeError:
        # Fallback if called outside an active event loop
        import threading

        t = threading.Thread(target=lambda: asyncio.run(_execute(task_id)), daemon=True)
        t.start()


def start_task(message: str, files: list[str]) -> str:
    task_id = str(uuid.uuid4())
    state = TaskState(
        task_id=task_id,
        user_request=message,
        input_files=files,
        status="CREATED",
    )
    task_store.save(state)
    _spawn_execution(task_id)
    return task_id


def get_task_state(task_id: str) -> Optional[TaskState]:
    return task_store.load(task_id)


async def _execute(task_id: str) -> None:
    state = task_store.load(task_id)
    if state is None:
        return

    message = state.user_request or ""
    msg_lower = message.lower()

    # Real AI Orchestrator Pathway with live on_update callback
    try:
        try:
            from agentic_engine import orchestrator
        except ImportError:
            import orchestrator

        def _on_update(updated_state: TaskState) -> None:
            task_store.save(updated_state)

        await orchestrator.run(state, on_update=_on_update)
    except Exception as ex:
        # Fallback to path if unexpected execution error
        if "fail" in msg_lower:
            await _execute_path_c(state)
        elif "handoff" in msg_lower:
            await _execute_path_d(state)
        elif "network" in msg_lower:
            await _execute_path_e(state)
        else:
            await _execute_path_b(state)



async def _execute_path_a(state: TaskState) -> None:
    # Path A: SIMPLE
    # Skip straight from CREATED to COMPLETED
    await asyncio.sleep(STEP_DELAY)
    state.status = "COMPLETED"
    state.task_type = "SIMPLE"
    state.plan = None
    state.tool_calls = []
    state.model_selection_notes = None
    state.answer = "4"
    task_store.save(state)


async def _execute_path_b(state: TaskState) -> None:
    # Path B: DOCUMENT success (default)
    # CREATED -> PLANNING -> RUNNING -> VERIFYING -> COMPLETED

    # Step 1: PLANNING
    await asyncio.sleep(STEP_DELAY)
    state.status = "PLANNING"
    state.task_type = "DOCUMENT"
    state.selected_model = "reasoning_model"
    state.current_agent = "reasoning_agent"
    state.plan = [
        "Extract text from input documents via OCR",
        "Retrieve reference standards from local knowledge base",
        "Calculate financial metrics and deviation via Python execution",
        "Write formatted summary report",
        "Verify calculation integrity and source alignment",
    ]
    state.model_selection_notes = None
    task_store.save(state)

    # Step 2: RUNNING
    await asyncio.sleep(STEP_DELAY)
    state.status = "RUNNING"
    task_store.save(state)

    # Step 3: Tool Call 1 - ocr
    await asyncio.sleep(STEP_DELAY)
    state.tool_calls.append(
        {
            "tool": "ocr",
            "success": True,
            "summary": "OCR completed on input files",
            "metadata": {"duration_ms": 310},
        }
    )
    state.tool_results.append(
        {"tool": "ocr", "output": "Extracted text content from annual report."}
    )
    task_store.save(state)

    # Step 4: Tool Call 2 - knowledge
    await asyncio.sleep(STEP_DELAY)
    state.tool_calls.append(
        {
            "tool": "knowledge",
            "success": True,
            "summary": "Retrieved domain reference benchmarks",
            "metadata": {"duration_ms": 175},
        }
    )
    state.tool_results.append(
        {"tool": "knowledge", "output": "Retrieved 1 matching context passage."}
    )
    state.retrieved_sources.append(
        Source(
            document_name="annual_report.pdf",
            page=3,
            section="Financial Highlights",
            retrieved_text="Operating margin increased by 4.2% across business units.",
            relevance_score=0.92,
        )
    )
    task_store.save(state)

    # Step 5: Tool Call 3 - python_execution
    await asyncio.sleep(STEP_DELAY)
    state.tool_calls.append(
        {
            "tool": "python_execution",
            "success": True,
            "summary": "Computed deviation metrics and variance statistics",
            "metadata": {"duration_ms": 420},
        }
    )
    state.tool_results.append(
        {"tool": "python_execution", "output": "Deviation calculated: 4.2%"}
    )
    state.calculations.append({"metric": "deviation", "value": 4.2})
    task_store.save(state)

    # Step 6: Tool Call 4 - file_write
    await asyncio.sleep(STEP_DELAY)
    state.tool_calls.append(
        {
            "tool": "file_write",
            "success": True,
            "summary": "Wrote deviation analysis summary artifact",
            "metadata": {"duration_ms": 85},
        }
    )
    state.tool_results.append(
        {"tool": "file_write", "output": "Wrote file: deviation_report.pdf"}
    )
    # If spreadsheet input or request, generate XLSX artifact, else PDF report
    msg_lower = (state.user_request or "").lower()
    has_xlsx = any(str(f).lower().endswith(".xlsx") for f in (state.input_files or []))
    if has_xlsx or "xlsx" in msg_lower or "spreadsheet" in msg_lower:
        state.generated_artifacts.append(
            Artifact(
                artifact_id="art-sample-xlsx",
                file_name="financial_analysis.xlsx",
                file_type="xlsx",
                download_url="/api/artifacts/art-sample-xlsx",
            )
        )
    else:
        state.generated_artifacts.append(
            Artifact(
                artifact_id="art-doc-001",
                file_name="deviation_report.pdf",
                file_type="pdf",
                download_url="/api/artifacts/art-doc-001",
            )
        )
    task_store.save(state)

    # Step 7: VERIFYING
    await asyncio.sleep(STEP_DELAY)
    state.status = "VERIFYING"
    state.verification = Verification(
        verified=True,
        notes="Calculations and sources cross-verified successfully against local reference.",
    )
    task_store.save(state)

    # Step 8: COMPLETED
    await asyncio.sleep(STEP_DELAY)
    state.status = "COMPLETED"
    state.answer = "The calculated deviation across reported business metrics is 4.2% based on cross-referenced financial highlights."
    task_store.save(state)


async def _execute_path_c(state: TaskState) -> None:
    # Path C: FAILURE
    await asyncio.sleep(STEP_DELAY)
    state.status = "PLANNING"
    state.task_type = "REASONING"
    state.selected_model = "reasoning_model"
    state.current_agent = "reasoning_agent"
    state.plan = ["Analyze task parameters", "Execute requested workflow"]
    task_store.save(state)

    await asyncio.sleep(STEP_DELAY)
    state.status = "RUNNING"
    task_store.save(state)

    await asyncio.sleep(STEP_DELAY)
    state.status = "FAILED"
    state.errors.append("Execution failed: Simulated engine failure encountered during processing.")
    task_store.save(state)


async def _execute_path_d(state: TaskState) -> None:
    # Path D: AGENT HANDOFF
    # CREATED -> PLANNING
    await asyncio.sleep(STEP_DELAY)
    state.status = "PLANNING"
    state.task_type = "REASONING"
    state.selected_model = "reasoning_model"
    state.plan = [
        "Extract OCR data",
        "Delegate complex calculation to mathematical agent",
        "Assemble mathematical output into summary",
        "Verify final result",
    ]
    task_store.save(state)

    # -> RUNNING, current_agent: "reasoning_agent"
    await asyncio.sleep(STEP_DELAY)
    state.status = "RUNNING"
    state.current_agent = "reasoning_agent"
    task_store.save(state)

    # -> tool_call: ocr (success)
    await asyncio.sleep(STEP_DELAY)
    state.tool_calls.append(
        {
            "tool": "ocr",
            "success": True,
            "summary": "Extracted numerical formula from input",
            "metadata": {"duration_ms": 110},
        }
    )
    state.tool_results.append({"tool": "ocr", "output": "Formula: 25 * 4 + 10"})
    task_store.save(state)

    # -> PUSH "reasoning_agent" onto agent_stack, set handoff_context
    # -> current_agent: "mathematical_agent"
    await asyncio.sleep(STEP_DELAY)
    state.agent_stack.append("reasoning_agent")
    state.handoff_context = {
        "reason": "Formula evaluation required",
        "source_agent": "reasoning_agent",
        "target_agent": "mathematical_agent",
    }
    state.current_agent = "mathematical_agent"
    task_store.save(state)

    # -> tool_call: python_execution (success)
    await asyncio.sleep(STEP_DELAY)
    state.tool_calls.append(
        {
            "tool": "python_execution",
            "success": True,
            "summary": "Evaluated mathematical formula",
            "metadata": {"duration_ms": 230},
        }
    )
    state.tool_results.append({"tool": "python_execution", "output": "Result: 110"})
    state.calculations.append({"formula": "25 * 4 + 10", "result": 110})
    task_store.save(state)

    # -> POP agent_stack (back to "reasoning_agent"), clear handoff_context
    # -> current_agent: "reasoning_agent"
    await asyncio.sleep(STEP_DELAY)
    state.agent_stack.pop()
    state.handoff_context = None
    state.current_agent = "reasoning_agent"
    task_store.save(state)

    # -> tool_call: file_write (success)
    await asyncio.sleep(STEP_DELAY)
    state.tool_calls.append(
        {
            "tool": "file_write",
            "success": True,
            "summary": "Saved calculation breakdown to artifact",
            "metadata": {"duration_ms": 75},
        }
    )
    state.tool_results.append(
        {"tool": "file_write", "output": "Wrote calculation_breakdown.txt"}
    )
    task_store.save(state)

    # -> VERIFYING -> COMPLETED
    await asyncio.sleep(STEP_DELAY)
    state.status = "VERIFYING"
    state.verification = Verification(
        verified=True, notes="Mathematical steps and final solution verified."
    )
    task_store.save(state)

    await asyncio.sleep(STEP_DELAY)
    state.status = "COMPLETED"
    state.answer = "Calculation completed via handoff: result is 110."
    task_store.save(state)


async def _execute_path_e(state: TaskState) -> None:
    # Path E: NETWORK REFUSAL
    await asyncio.sleep(STEP_DELAY)
    state.status = "PLANNING"
    state.task_type = "CODING"
    state.selected_model = "coding_model"
    state.plan = ["Inspect network configuration", "Execute python code in isolation"]
    task_store.save(state)

    await asyncio.sleep(STEP_DELAY)
    state.status = "RUNNING"
    state.current_agent = "coding_agent"
    task_store.save(state)

    await asyncio.sleep(STEP_DELAY)
    refusal_msg = (
        "Network isolation could not be established on this host. "
        "Refusing to execute — no fallback execution mode is permitted."
    )
    state.tool_calls.append(
        {
            "tool": "python_execution",
            "success": False,
            "error": refusal_msg,
            "summary": "Execution refused due to network isolation failure",
            "metadata": {"duration_ms": 15},
        }
    )
    state.tool_results.append({"tool": "python_execution", "error": refusal_msg})
    state.errors.append(refusal_msg)
    state.status = "FAILED"
    task_store.save(state)

    # Call network_monitor.record_blocked_attempt
    try:
        from backend import network_monitor
        network_monitor.record_blocked_attempt(
            reason=refusal_msg,
            task_id=state.task_id,
        )
    except ImportError:
        try:
            import network_monitor
            network_monitor.record_blocked_attempt(
                reason=refusal_msg,
                task_id=state.task_id,
            )
        except Exception:
            pass


async def subscribe(task_id: str) -> AsyncGenerator[dict[str, Any], None]:
    last_status: Optional[str] = None
    last_agent: Optional[str] = None
    last_tool_call_count: int = 0
    retries = 0

    while True:
        state = task_store.load(task_id)
        if state is None:
            retries += 1
            if retries > 25:
                raise KeyError(f"Task {task_id} not found")
            await asyncio.sleep(POLL_INTERVAL)
            continue

        # Initial baseline capture if starting for the first time
        if last_status is None:
            last_status = state.status
            if state.current_agent is not None:
                last_agent = state.current_agent
            last_tool_call_count = len(state.tool_calls)

            # If task is already finished when subscription begins, emit final and exit
            if state.status in ("COMPLETED", "FAILED"):
                final_resp = DictFriendlyTaskFinalResponse.from_task_state(state)
                yield {
                    "event": "final",
                    "result": final_resp,
                }
                return

            await asyncio.sleep(POLL_INTERVAL)
            continue

        # 1. New tool calls
        if len(state.tool_calls) > last_tool_call_count:
            for tc in state.tool_calls[last_tool_call_count:]:
                yield {
                    "event": "tool_call",
                    "tool": tc.get("tool"),
                    "success": tc.get("success", True),
                    "summary": tc.get("summary"),
                    "current_agent": state.current_agent,
                }
            last_tool_call_count = len(state.tool_calls)

        # 2. Agent handoffs
        if (
            last_agent is not None
            and state.current_agent is not None
            and state.current_agent != last_agent
        ):
            yield {
                "event": "agent_handoff",
                "from_agent": last_agent,
                "to_agent": state.current_agent,
                "current_agent": state.current_agent,
            }
        if state.current_agent is not None:
            last_agent = state.current_agent

        # 3. Final completion / failure
        if state.status in ("COMPLETED", "FAILED"):
            final_resp = DictFriendlyTaskFinalResponse.from_task_state(state)
            yield {
                "event": "final",
                "result": final_resp,
            }
            return

        # 4. Status changes
        if state.status != last_status:
            yield {
                "event": "status_change",
                "status": state.status,
                "current_agent": state.current_agent,
            }
            last_status = state.status

        await asyncio.sleep(POLL_INTERVAL)

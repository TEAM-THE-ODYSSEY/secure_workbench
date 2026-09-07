from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from .agents import (
    CodingAgent,
    DocumentAgent,
    KnowledgeAgent,
    MathematicalAgent,
    MultimodalAgent,
    PIDAgent,
    ReasoningAgent,
)
from .config import Settings
from .document_output import DocumentOutput
from .extractors import extract
from .guardrails.input_guard import InputGuard, SecurityDecision
from .knowledge import KnowledgeRetriever
from .llm import OllamaClient
from .models.registry import ModelProfile
from .models.resources import ResourceMonitor
from .models.selector import ModelCapabilityUnavailableError, ModelSelector
from .observability.tracer import Tracer
from .orchestration.execution_plan import ExecutionPlan
from .orchestration.planner import ExecutionPlanner
from .orchestration.policy import PolicyEngine
from .orchestration.router import CapabilityRouter
from .runtime.budgets import BudgetTracker, ExecutionBudget
from .runtime.context import ScopedContext
from .runtime.executor import ExecutionCoordinator
from .runtime.scheduler import DAGScheduler
from .runtime.state import ExecutionState, StateTracker
from .session_store import SessionStore
from .validators.base import ValidationResult
from .validators.registry import build_validator_chain, get_default_chain_for_task

logger = logging.getLogger("agentic_engine")


class AgenticEngine:
    """Canonical Execution Engine for Air-Gapped Sovereign AI.
    
    Guarantees deterministic, capability-driven, resource-aware, validated,
    and observable multi-agent execution.
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()
        self.store = SessionStore(self.settings.db_path)
        self.llm = OllamaClient(self.settings)
        self.guard = InputGuard()
        self.planner = ExecutionPlanner(self.llm)
        self.resources = ResourceMonitor()
        self.selector = ModelSelector(self.resources)
        self.router = CapabilityRouter()
        self.policy = PolicyEngine()
        self.retriever = KnowledgeRetriever()
        self.doc_output = DocumentOutput()
        self.dag_scheduler = DAGScheduler(max_concurrency=4)

        # Agent Registry with Capability Contracts
        self.agents: Dict[str, Any] = {
            "reasoning": ReasoningAgent(self.llm),
            "mathematics": MathematicalAgent(self.llm),
            "mathematical": MathematicalAgent(self.llm),  # Alias
            "coding": CodingAgent(self.llm),
            "document": DocumentAgent(self.llm),
            "knowledge": KnowledgeAgent(self.llm, self.retriever),
            "multimodal": MultimodalAgent(self.llm),
            "pid": PIDAgent(self.llm),
        }

        # Runtime Execution Coordinator
        self.executor = ExecutionCoordinator(
            agents=self.agents,
            model_selector=self.selector,
            validator_runner_fn=self._run_validator_chain,
            doc_output_fn=self.doc_output.create,
        )

    def new_chat(self) -> str:
        return self.store.create_chat()

    def _run_validator_chain(
        self,
        chain_name_or_list: Any,
        output: str,
        user_request: str,
        execution_result: Any = None,
    ) -> ValidationResult:
        if isinstance(chain_name_or_list, (list, tuple)):
            names = list(chain_name_or_list)
        elif isinstance(chain_name_or_list, str):
            names = [chain_name_or_list]
        else:
            names = ["text"]
        chain = build_validator_chain(names)
        return chain.validate(
            output=output,
            user_request=user_request,
            execution=execution_result,
        )

    def execute(
        self,
        message: str = "",
        file_path: Optional[str] = None,
        chat_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Canonical entry point executing the non-negotiable 16-step architecture."""
        active_chat_id = chat_id or session_id or self.new_chat()
        request_id = f"req_{uuid.uuid4().hex[:8]}"
        trace = Tracer.start_trace(request_id=request_id)
        span_total = trace.start_span("total_execution")

        # 1. Input Normalization & Extraction
        span_norm = trace.start_span("input_normalization")
        file_content = ""
        if file_path:
            try:
                extracted = extract(file_path)
                file_content = extracted.get("text", "")
            except Exception as e:
                file_content = f"[File extraction notice: {e}]"
        span_norm.finish()

        # 2. Security Gate & Trust Policy Check
        span_sec = trace.start_span("security_policy_check")
        allowed, reason, meta = self.guard.check(message, file_path, file_content)
        span_sec.finish(decision=meta.get("decision", "ACCEPT"))

        if not allowed:
            self.store.add(
                active_chat_id,
                "system",
                f"Request blocked before LLM: {reason}",
                {"blocked": True, "security": meta},
            )
            span_total.finish(status="BLOCKED")
            return {
                "chat_id": active_chat_id,
                "request_id": request_id,
                "trace_id": trace.trace_id,
                "status": "blocked",
                "blocked": True,
                "task": "blocked",
                "task_type": "blocked",
                "complexity": "none",
                "capabilities": [],
                "agent": "security_gate",
                "model": "none",
                "tools": [],
                "answer": f"Request blocked by pre-LLM security gate: {reason}",
                "security": meta,
                "validation": {"valid": False, "reason": reason},
                "artifacts": {},
                "latency": {"total_ms": span_sec.duration_ms},
            }

        # 3. Task Classification, Complexity Analysis, and Planning
        span_plan = trace.start_span("planning")
        plan: ExecutionPlan = self.planner.plan(
            text=message,
            context_chars=len(file_content),
            has_file=bool(file_path),
            file_path=file_path,
        )
        span_plan.finish(task_type=plan.task_type, complexity=plan.complexity)

        # 4. Knowledge Retrieval (if plan requires retrieval)
        retrieved_items = []
        if plan.retrieval or "knowledge_retriever" in plan.tools:
            span_retrieval = trace.start_span("retrieval")
            try:
                retrieved_items = self.retriever.search(message, limit=5)
            except Exception as e:
                logger.warning(f"Knowledge retrieval error: {e}")
            span_retrieval.finish(count=len(retrieved_items))

        # 5. Build Scoped Execution Context
        context = ScopedContext(
            request_id=request_id,
            session_id=active_chat_id,
            task_context=message,
            conversation_context=self.store.history(active_chat_id, self.settings.max_history),
            retrieved_context=retrieved_items,
            file_path=file_path,
            file_content=file_content,
        )

        # 6. Execute DAG or Agent via Execution Coordinator
        span_exec = trace.start_span("agent_execution", agent=plan.agent)
        try:
            res = self.executor.execute(
                plan=plan,
                context=context,
                replan_callback_fn=lambda directive, feedback: self.planner.plan(
                    text=f"{directive}\n[Validator Feedback: {feedback}]",
                    context_chars=len(file_content),
                    has_file=bool(file_path),
                    file_path=file_path,
                ),
            )
        except ModelCapabilityUnavailableError as mc_err:
            span_exec.finish(status="MODEL_CAPABILITY_UNAVAILABLE")
            span_total.finish(status="FAILED")
            return {
                "chat_id": active_chat_id,
                "request_id": request_id,
                "trace_id": trace.trace_id,
                "status": "failed",
                "blocked": False,
                "task": plan.task_type,
                "task_type": plan.task_type,
                "plan": plan.to_dict(),
                "complexity": plan.complexity,
                "capabilities": plan.capabilities,
                "agent": plan.agent,
                "model": "unavailable",
                "tools": plan.tools,
                "answer": f"Task execution halted: {mc_err}",
                "error": str(mc_err),
                "validated": False,
                "artifacts": {},
                "trace": trace.to_dict(),
            }

        span_exec.finish(status=res.get("status", "COMPLETED"))
        span_total.finish()

        # 7. Persist to Session Store
        self.store.add(
            active_chat_id,
            "user",
            message or "[file upload]",
            {"plan": plan.to_dict(), "model": res.get("model", "")},
        )
        self.store.add(
            active_chat_id,
            "assistant",
            res.get("answer", ""),
            {
                "plan": plan.to_dict(),
                "model": res.get("model", ""),
                "validation": res.get("validation", {}),
                "status": res.get("status", ""),
            },
        )

        # 8. Enrich Response Contract
        res["chat_id"] = active_chat_id
        res["request_id"] = request_id
        res["trace_id"] = trace.trace_id
        res["blocked"] = False
        res["task"] = plan.task_type
        res["plan"] = plan.to_dict()
        res["validated"] = res.get("validation", {}).get("valid", False)

        # Attach hardware / resource telemetry to trace
        snap = self.resources.get_snapshot()
        trace_data = trace.to_dict()
        trace_data["resources"] = {
            "has_cuda": snap.has_cuda,
            "vram_available_mb": snap.vram_available_mb,
            "vram_total_mb": snap.vram_total_mb,
            "ram_available_mb": snap.ram_available_mb,
            "cpu_percent": snap.cpu_percent,
        }
        res["trace"] = trace_data

        return res

    def run(self, chat_id: str, message: str = "", file_path: str | None = None) -> Dict[str, Any]:
        """Backward-compatible run() method matching existing orchestrator signatures."""
        return self.execute(message=message, file_path=file_path, chat_id=chat_id)


# Backward-compatible alias
Orchestrator = AgenticEngine

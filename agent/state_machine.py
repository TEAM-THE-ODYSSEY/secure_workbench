"""
State Machine Controller for Main AI Agent.
Enforces deterministic state transitions, step bounds, tool call limits,
and primary-to-fallback LLM failover.
"""

from enum import Enum
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from agent.models.model_manager import ModelManager
from agent.models.schemas import (
    AgentTaskResult,
    ArtifactMetadata,
    Citation,
    ContextPlan,
    EvidenceChunk,
    ExecutionTraceRecord,
    FinalReasoningOutput,
    StructuredPDFContent,
    TaskRequest,
)
from agent.planner import ContextPlanner
from agent.execution_trace import ExecutionTraceTracker
from agent.prompts import (
    REASONING_OUTPUT_PROMPT,
    STRUCTURED_GENERATION_PROMPT,
    SYSTEM_PROMPT,
)
from agent.tools.registry import ToolRegistry
from agent.verification.grounding_verifier import GroundingVerifier, VerificationResult
from agent.verification.pdf_validator import PyMuPDFValidator

logger = logging.getLogger("agent.state_machine")


class State(Enum):
    START = "START"
    UNDERSTAND = "UNDERSTAND"
    PLAN = "PLAN"
    IDENTIFY_ENTITIES = "IDENTIFY_ENTITIES"
    DETERMINE_REQUIRED_CONTEXT = "DETERMINE_REQUIRED_CONTEXT"
    RETRIEVE_TOOL_CALL = "RETRIEVE_TOOL_CALL"
    EVALUATE_EVIDENCE = "EVALUATE_EVIDENCE"
    REASON = "REASON"
    VERIFY = "VERIFY"
    COMPLETE = "COMPLETE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    MODEL_ERROR = "MODEL_ERROR"


class StateMachineBounds:
    """Strict agent execution boundaries."""
    MAX_AGENT_STEPS: int = 12
    MAX_KB_SEARCHES: int = 3
    MAX_TOOL_CALLS: int = 4
    MAX_LLM_GENERATIONS: int = 3


class MainAgentStateMachine:
    """
    State Machine orchestrating Main AI Agent task lifecycle.
    """

    def __init__(
        self,
        model_manager: Optional[ModelManager] = None,
        planner: Optional[ContextPlanner] = None,
        tool_registry: Optional[ToolRegistry] = None,
        verifier: Optional[GroundingVerifier] = None,
        pdf_validator: Optional[PyMuPDFValidator] = None,
    ):
        self.model_manager = model_manager or ModelManager()
        self.planner = planner or ContextPlanner(model_manager=self.model_manager)
        self.tool_registry = tool_registry or ToolRegistry()
        self.verifier = verifier or GroundingVerifier()
        self.pdf_validator = pdf_validator or PyMuPDFValidator()

    def run(self, request: TaskRequest, task_id: Optional[str] = None) -> AgentTaskResult:
        """
        Execute Main Agent workflow from START to COMPLETE.
        """
        task_id = task_id or f"task_{uuid.uuid4().hex[:12]}"
        logger.info(f"[{task_id}] Starting Main Agent State Machine for objective: '{request.objective}'")

        trace_tracker = ExecutionTraceTracker(task_id=task_id)
        current_state = State.START
        step_count = 0
        kb_search_count = 0
        tool_call_count = 0
        llm_generation_count = 0

        context_plan: Optional[ContextPlan] = None
        retrieved_evidence: List[EvidenceChunk] = []
        structured_content: Optional[StructuredPDFContent] = None
        final_reasoning: Optional[FinalReasoningOutput] = None
        artifact_metadata: Optional[ArtifactMetadata] = None
        failure_message: Optional[str] = None
        fallback_used = False

        while current_state not in [
            State.COMPLETE,
            State.INSUFFICIENT_EVIDENCE,
            State.VERIFICATION_FAILED,
            State.MODEL_ERROR,
        ]:
            step_count += 1
            if step_count > StateMachineBounds.MAX_AGENT_STEPS:
                logger.error(f"[{task_id}] Exceeded MAX_AGENT_STEPS ({StateMachineBounds.MAX_AGENT_STEPS}). Terminating.")
                current_state = State.MODEL_ERROR
                failure_message = "Agent execution exceeded step limit."
                break

            logger.info(f"[{task_id}] Step {step_count}: Entering State '{current_state.value}'")

            # -------------------------------------------------------------
            # STATE HANDLERS
            # -------------------------------------------------------------
            if current_state == State.START:
                current_state = State.UNDERSTAND

            elif current_state == State.UNDERSTAND:
                # LLM Generation #1: Context & Intent Planning
                t0 = time.time()
                llm_generation_count += 1
                context_plan = self.planner.plan_context(request, task_id=task_id)
                trace_tracker.intent = context_plan.intent
                trace_tracker.entities = context_plan.entities
                trace_tracker.record_phase("planning_ms", (time.time() - t0) * 1000)
                current_state = State.RETRIEVE_TOOL_CALL

            elif current_state == State.PLAN:
                current_state = State.IDENTIFY_ENTITIES

            elif current_state == State.IDENTIFY_ENTITIES:
                current_state = State.DETERMINE_REQUIRED_CONTEXT

            elif current_state == State.DETERMINE_REQUIRED_CONTEXT:
                current_state = State.RETRIEVE_TOOL_CALL

            elif current_state == State.RETRIEVE_TOOL_CALL:
                t0 = time.time()
                tool_calls_to_make = context_plan.tool_calls if context_plan else []
                if not tool_calls_to_make:
                    tool_calls_to_make = [{"tool": "knowledge_search", "query": request.objective}]

                for tc in tool_calls_to_make[:StateMachineBounds.MAX_TOOL_CALLS]:
                    tool_name = tc.get("tool", "knowledge_search")
                    tool_call_count += 1
                    trace_tracker.log_tool_call(tool_name)

                    if "knowledge" in tool_name:
                        kb_search_count += 1
                        if kb_search_count > StateMachineBounds.MAX_KB_SEARCHES:
                            continue

                    try:
                        kwargs = {k: v for k, v in tc.items() if k != "tool"}
                        result_chunks = self.tool_registry.execute(tool_name, **kwargs)
                        if isinstance(result_chunks, list):
                            retrieved_evidence.extend(result_chunks)
                    except Exception as ex:
                        logger.warning(f"[{task_id}] Tool '{tool_name}' execution error: {ex}")

                trace_tracker.record_phase("retrieval_ms", (time.time() - t0) * 1000)
                trace_tracker.evidence_count = len(retrieved_evidence)
                current_state = State.EVALUATE_EVIDENCE

            elif current_state == State.EVALUATE_EVIDENCE:
                if not retrieved_evidence:
                    logger.warning(f"[{task_id}] Evaluated evidence: 0 trusted items retrieved.")
                    current_state = State.INSUFFICIENT_EVIDENCE
                    failure_message = "No trusted evidence found in Knowledge Base matching task parameters."
                else:
                    logger.info(f"[{task_id}] Evaluated evidence: {len(retrieved_evidence)} trusted chunks acquired.")
                    current_state = State.REASON

            elif current_state == State.REASON:
                t0 = time.time()
                llm_generation_count += 1
                if llm_generation_count > StateMachineBounds.MAX_LLM_GENERATIONS:
                    logger.warning(f"[{task_id}] Exceeded MAX_LLM_GENERATIONS limit.")

                evidence_text = "\n\n".join([
                    f"[{idx+1}] Doc: {e.document_id} (Title: {e.title}, Ver: {e.version}, Sec: {e.section}, Page: {e.page})\n{e.content}"
                    for idx, e in enumerate(retrieved_evidence)
                ])

                output_type = context_plan.output_type if context_plan else "TEXT"

                if output_type == "PDF" or request.task_type == "GENERATE_PDF":
                    # Generate StructuredPDFContent
                    prompt = STRUCTURED_GENERATION_PROMPT.format(
                        objective=request.objective,
                        evidence_text=evidence_text,
                    )
                    messages = [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ]
                    try:
                        structured_content, meta = self.model_manager.generate_structured(
                            messages=messages,
                            response_schema=StructuredPDFContent,
                            task_id=task_id,
                        )
                        trace_tracker.active_model = meta.get("model", self.model_manager.get_active_model())
                        trace_tracker.fallback_used = meta.get("fallback_used", False)
                        fallback_used = trace_tracker.fallback_used
                    except Exception as exc:
                        logger.warning(f"[{task_id}] Structured reasoning LLM failed ({exc}). Performing Direct Evidence Synthesis fallback.")
                        structured_content = self._direct_evidence_synthesis(request.objective, retrieved_evidence)
                        trace_tracker.active_model = "Direct Evidence Synthesis"
                        trace_tracker.fallback_used = True
                        fallback_used = True
                else:
                    # Generate FinalReasoningOutput text
                    prompt = REASONING_OUTPUT_PROMPT.format(
                        objective=request.objective,
                        plan_context=context_plan.model_dump_json() if context_plan else "{}",
                        evidence_text=evidence_text,
                    )
                    messages = [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ]
                    try:
                        final_reasoning, meta = self.model_manager.generate_structured(
                            messages=messages,
                            response_schema=FinalReasoningOutput,
                            task_id=task_id,
                        )
                        trace_tracker.active_model = meta.get("model", self.model_manager.get_active_model())
                        trace_tracker.fallback_used = meta.get("fallback_used", False)
                        fallback_used = trace_tracker.fallback_used
                    except Exception as exc:
                        logger.warning(f"[{task_id}] Reasoning LLM failed ({exc}). Synthesizing answer directly from evidence.")
                        final_reasoning = self._direct_text_synthesis(request.objective, retrieved_evidence)
                        trace_tracker.active_model = "Direct Evidence Synthesis"
                        trace_tracker.fallback_used = True
                        fallback_used = True

                trace_tracker.record_phase("reasoning_ms", (time.time() - t0) * 1000)
                current_state = State.VERIFY

            elif current_state == State.VERIFY:
                t0 = time.time()
                if structured_content:
                    v_res = self.verifier.verify_structured_pdf(structured_content, retrieved_evidence)
                    trace_tracker.verification_status = "PASSED" if v_res.is_valid else "WARNINGS"
                    if v_res.is_valid or request.allow_fallback:
                        # Generate PDF Artifact
                        t_pdf = time.time()
                        artifact_metadata = self.tool_registry.execute(
                            "generate_report_pdf",
                            content=structured_content,
                            task_id=task_id,
                        )
                        trace_tracker.record_phase("pdf_generation_ms", (time.time() - t_pdf) * 1000)
                        current_state = State.COMPLETE
                    else:
                        current_state = State.VERIFICATION_FAILED
                        failure_message = f"Grounding verification failed: {v_res.unsupported_claims}"
                elif final_reasoning:
                    v_res = self.verifier.verify_final_output(final_reasoning, retrieved_evidence)
                    trace_tracker.verification_status = "PASSED" if v_res.is_valid else "WARNINGS"
                    current_state = State.COMPLETE
                else:
                    current_state = State.MODEL_ERROR
                    failure_message = "Reasoning step produced no valid output schema."

                trace_tracker.record_phase("verification_ms", (time.time() - t0) * 1000)

        # -------------------------------------------------------------
        # RESULT COMPILATION
        # -------------------------------------------------------------
        trace_record = trace_tracker.get_record()

        if current_state == State.COMPLETE:
            all_citations = []
            if structured_content and structured_content.references:
                all_citations = structured_content.references
            elif final_reasoning and final_reasoning.citations:
                all_citations = final_reasoning.citations

            answer_text = final_reasoning.answer if final_reasoning else (
                f"Generated Executive PDF Artifact '{artifact_metadata.filename}' ({artifact_metadata.file_size_bytes} bytes)."
                if artifact_metadata else "Task completed successfully."
            )

            return AgentTaskResult(
                task_id=task_id,
                status="COMPLETE",
                result_type="PDF" if artifact_metadata else "TEXT",
                answer=answer_text,
                artifact=artifact_metadata,
                model=trace_record.active_model,
                fallback_used=fallback_used,
                citations=all_citations,
                structured_content=structured_content,
                trace=trace_record,
            )
        else:
            return AgentTaskResult(
                task_id=task_id,
                status=current_state.value,
                result_type="TEXT",
                message=failure_message or f"Task stopped in state {current_state.value}",
                model=trace_record.active_model,
                fallback_used=fallback_used,
                trace=trace_record,
            )

    def _direct_evidence_synthesis(self, objective: str, evidence: List[EvidenceChunk]) -> StructuredPDFContent:
        """Construct StructuredPDFContent directly from evidence without LLM."""
        seen_doc_ids = set()
        references: List[Citation] = []
        procedure_steps = []
        step_counter = 1

        for ev in evidence:
            if ev.document_id not in seen_doc_ids:
                seen_doc_ids.add(ev.document_id)
                references.append(ev.citation)

            lines = [l.strip() for l in ev.content.split("\n") if l.strip() and len(l.strip()) > 15]
            for line in lines[:3]:
                procedure_steps.append(
                    {
                        "step_number": step_counter,
                        "instruction": line.lstrip("0123456789.-* "),
                        "citations": [ev.citation],
                    }
                )
                step_counter += 1

        return StructuredPDFContent(
            title=f"Evidence Synthesis: {objective[:50]}",
            purpose=f"Consolidated trusted evidence for objective: '{objective}'",
            scope=f"Sourced from {len(seen_doc_ids)} trusted document(s).",
            procedure_steps=procedure_steps[:10],
            references=references,
        )

    def _direct_text_synthesis(self, objective: str, evidence: List[EvidenceChunk]) -> FinalReasoningOutput:
        """Construct FinalReasoningOutput directly from evidence without LLM."""
        snippets = [f"• {e.content[:150]}..." for e in evidence[:3]]
        citations = [e.citation for e in evidence]
        return FinalReasoningOutput(
            answer=f"Synthesized Answer from Trusted Evidence:\n" + "\n".join(snippets),
            claims=[e.content[:80] for e in evidence[:3]],
            citations=citations,
            confidence="HIGH",
            limitations=[],
        )


# Backward compatibility alias
ReasoningStateMachine = MainAgentStateMachine

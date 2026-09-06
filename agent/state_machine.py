"""
Bounded State Machine for the Reasoning Mini-Agent V1.
Controls state transitions, loop safety, step limits, evidence checking, content verification, and PDF generation.
Includes direct evidence synthesis when LLM endpoints are unavailable.
"""

from enum import Enum
import logging
import uuid
from typing import Any, Dict, List, Optional

from agent.model_manager import InfrastructureError, ModelManager, QualityFailureError
from agent.models import (
    AgentTaskResult,
    ArtifactMetadata,
    Citation,
    EvidenceChunk,
    OperatingLimit,
    ProcedureStep,
    StructuredPDFContent,
    TaskRequest,
)
from agent.pdf_generator import ReportLabPDFGenerator
from agent.pdf_validator import PyMuPDFValidator
from agent.prompts import (
    STRUCTURED_GENERATION_PROMPT,
    SYSTEM_PROMPT,
    TASK_UNDERSTANDING_PROMPT,
)
from agent.tools import KnowledgeTool, ToolRegistry
from agent.verifier import ContentVerifier
from rag.storage.minio_storage import minio_client

logger = logging.getLogger("agent.state_machine")


class State(str, Enum):
    START = "START"
    UNDERSTAND_TASK = "UNDERSTAND_TASK"
    RETRIEVE_EVIDENCE = "RETRIEVE_EVIDENCE"
    REASON = "REASON"
    BUILD_STRUCTURED_CONTENT = "BUILD_STRUCTURED_CONTENT"
    VERIFY_CONTENT = "VERIFY_CONTENT"
    GENERATE_PDF = "GENERATE_PDF"
    VERIFY_PDF = "VERIFY_PDF"
    COMPLETE = "COMPLETE"

    # Terminal Failure States
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    PDF_GENERATION_FAILED = "PDF_GENERATION_FAILED"
    TOOL_ERROR = "TOOL_ERROR"
    MODEL_ERROR = "MODEL_ERROR"


class StateMachineConfig:
    """State machine bounds and retry limits."""
    MAX_STEPS: int = 12
    MAX_KB_SEARCHES: int = 3
    MAX_TOOL_CALLS: int = 5
    MAX_REASONING_RETRIES: int = 2


def _clean_query(raw_query: str) -> str:
    """Strip meta-instruction prefixes like 'Generate a PDF of...' to isolate underlying search terms."""
    q = raw_query.strip()
    prefixes = [
        "synthesize standard operating procedure for",
        "synthesize standard operating procedure of",
        "synthesize sop for",
        "synthesize sop of",
        "synthesize procedure steps for",
        "synthesize procedure steps of",
        "synthesize procedure for",
        "synthesize procedure of",
        "synthesize",
        "generate a pdf of the content of",
        "generate pdf of the content of",
        "generate a pdf of the",
        "generate pdf of the",
        "generate a pdf of",
        "generate pdf of",
        "generate a pdf for",
        "generate pdf for",
        "generate a pdf about",
        "generate pdf about",
        "create a pdf of",
        "create pdf of",
        "export to pdf",
    ]
    for prefix in prefixes:
        if q.lower().startswith(prefix):
            q = q[len(prefix):].strip()
            break
    return q if q else raw_query


def _synthesize_from_evidence(
    objective: str,
    evidence: List[EvidenceChunk],
) -> StructuredPDFContent:
    """
    Build a StructuredPDFContent directly from retrieved evidence
    without LLM reasoning. Used as a fallback when all LLM endpoints are offline.
    Parses parameters, safety rules, warnings, and procedural steps from chunk content.
    """
    clean_title = _clean_query(objective).strip().title()
    title = clean_title if clean_title else "Knowledge Base Evidence Report"

    seen_doc_ids = set()
    references: List[Citation] = []
    procedure_steps: List[ProcedureStep] = []
    operating_limits: List[OperatingLimit] = []
    safety_requirements: List[str] = []
    warnings: List[str] = []
    preconditions: List[str] = []

    step_counter = 1

    for ev in evidence:
        # Build unique references
        if ev.document_id not in seen_doc_ids:
            seen_doc_ids.add(ev.document_id)
            references.append(
                Citation(
                    document_id=ev.document_id,
                    title=ev.title,
                    version=ev.version,
                    section=ev.section,
                    page=ev.page,
                    trust_level="TRUSTED",
                )
            )

        citation_ref = Citation(
            document_id=ev.document_id,
            title=ev.title,
            version=ev.version,
            section=ev.section,
            page=ev.page,
            trust_level="TRUSTED",
        )

        lines = [l.strip() for l in ev.content.split("\n") if l.strip()]
        for line in lines:
            # Skip decorative headers
            if line.startswith("=") or line.startswith("# ===") or line.startswith("---"):
                continue

            # Check for Operating Limits (e.g. "Maximum Operating Temperature: 345 °C")
            if ":" in line and any(unit_tag in line.lower() for unit_tag in ["°c", "kg/cm2", "lpm", "bar", "psi", "rpm", "m3/h", "%", "mm"]):
                parts = line.lstrip("- ").lstrip("* ").split(":", 1)
                if len(parts) == 2:
                    param = parts[0].strip()
                    val = parts[1].strip()
                    operating_limits.append(OperatingLimit(parameter=param, value=val, citations=[citation_ref]))
                    continue

            # Check for Safety Requirements
            if any(s_term in line.lower() for s_term in ["ppe", "personal protective equipment", "safety goggles", "h2s monitor", "gloves"]):
                safety_req = line.lstrip("- ").lstrip("* ").strip()
                if safety_req and safety_req not in safety_requirements:
                    safety_requirements.append(safety_req)
                continue

            # Check for Warnings
            if any(w_term in line.lower() for w_term in ["warning:", "caution:", "danger:", "critical:"]):
                warn_text = line.lstrip("- ").lstrip("* ").strip()
                if warn_text and warn_text not in warnings:
                    warnings.append(warn_text)
                continue

            # Check for Preconditions
            if any(p_term in line.lower() for p_term in ["pre-startup", "checklist", "ensure suction", "verify lube"]):
                precond = line.lstrip("- ").lstrip("* ").strip()
                if precond and len(precond) > 10 and precond not in preconditions:
                    preconditions.append(precond)

            # Standard Procedure Instructions
            if len(line) > 15 and not line.isupper():
                instruction_text = line.lstrip("0123456789.-* ").strip()
                if instruction_text and len(instruction_text) > 10:
                    procedure_steps.append(
                        ProcedureStep(
                            step_number=step_counter,
                            instruction=instruction_text,
                            citations=[citation_ref],
                        )
                    )
                    step_counter += 1

    # Fallback if no steps parsed cleanly
    if not procedure_steps:
        for idx, ev in enumerate(evidence, 1):
            procedure_steps.append(
                ProcedureStep(
                    step_number=idx,
                    instruction=ev.content.strip(),
                    citations=[
                        Citation(
                            document_id=ev.document_id,
                            title=ev.title,
                            version=ev.version,
                            section=ev.section,
                            page=ev.page,
                            trust_level="TRUSTED",
                        )
                    ],
                )
            )

    doc_titles = list({ev.title for ev in evidence})
    purpose = f"This document consolidates trusted evidence from the Knowledge Base relevant to: '{_clean_query(objective)}'"
    scope = f"Evidence sourced from {len(seen_doc_ids)} trusted document(s): {', '.join(doc_titles[:3])}"

    return StructuredPDFContent(
        title=title,
        purpose=purpose,
        scope=scope,
        preconditions=preconditions[:5],
        safety_requirements=safety_requirements[:5],
        procedure_steps=procedure_steps[:15],
        operating_limits=operating_limits[:10],
        warnings=warnings[:5],
        references=references,
    )


class ReasoningStateMachine:
    """
    Controlled Python State Machine orchestrating reasoning tasks.
    """

    def __init__(
        self,
        model_manager: Optional[ModelManager] = None,
        tool_registry: Optional[ToolRegistry] = None,
        verifier: Optional[ContentVerifier] = None,
        pdf_generator: Optional[ReportLabPDFGenerator] = None,
        pdf_validator: Optional[PyMuPDFValidator] = None,
    ):
        self.model_manager = model_manager or ModelManager()
        self.tool_registry = tool_registry or ToolRegistry()
        self.verifier = verifier or ContentVerifier()
        self.pdf_generator = pdf_generator or ReportLabPDFGenerator()
        self.pdf_validator = pdf_validator or PyMuPDFValidator()

    def run(self, request: TaskRequest, task_id: Optional[str] = None) -> AgentTaskResult:
        """
        Execute the state machine from START to COMPLETE or failure state.
        """
        task_id = task_id or f"task_{uuid.uuid4().hex[:12]}"
        logger.info(f"[{task_id}] Starting Reasoning State Machine for objective: '{request.objective}'")

        current_state = State.START
        step_count = 0
        kb_search_count = 0
        reasoning_retry_count = 0
        used_direct_synthesis = False

        search_query: str = request.objective
        retrieved_evidence: List[EvidenceChunk] = []
        structured_content: Optional[StructuredPDFContent] = None
        pdf_bytes: Optional[bytes] = None
        artifact_metadata: Optional[ArtifactMetadata] = None
        all_citations: List[Citation] = []
        failure_message: Optional[str] = None

        while current_state not in [
            State.COMPLETE,
            State.INSUFFICIENT_EVIDENCE,
            State.VERIFICATION_FAILED,
            State.PDF_GENERATION_FAILED,
            State.TOOL_ERROR,
            State.MODEL_ERROR,
        ]:
            step_count += 1
            if step_count > StateMachineConfig.MAX_STEPS:
                logger.error(f"[{task_id}] Exceeded MAX_STEPS limit ({StateMachineConfig.MAX_STEPS}). Terminating.")
                current_state = State.MODEL_ERROR
                failure_message = "Execution exceeded maximum state machine step limit."
                break

            logger.info(f"[{task_id}] State Machine Step {step_count}: Entering State '{current_state.value}'")

            # State Handlers
            if current_state == State.START:
                current_state = State.UNDERSTAND_TASK

            elif current_state == State.UNDERSTAND_TASK:
                search_query = _clean_query(request.objective)
                if request.entities:
                    search_query += f" entity:{request.entities[0]}"
                current_state = State.RETRIEVE_EVIDENCE

            elif current_state == State.RETRIEVE_EVIDENCE:
                kb_search_count += 1
                if kb_search_count > StateMachineConfig.MAX_KB_SEARCHES:
                    logger.warning(f"[{task_id}] Exceeded MAX_KB_SEARCHES limit.")
                    current_state = State.INSUFFICIENT_EVIDENCE
                    failure_message = "The trusted knowledge base search did not yield sufficient evidence after maximum retries."
                    break

                try:
                    evidence_result: List[EvidenceChunk] = self.tool_registry.execute(
                        "knowledge_search",
                        query=search_query,
                        entity_ids=request.entities,
                        document_type=request.document_type,
                        version=request.version_constraint,
                    )
                    retrieved_evidence = evidence_result

                    if not retrieved_evidence:
                        logger.warning(f"[{task_id}] Search returned 0 trusted evidence items.")
                        current_state = State.INSUFFICIENT_EVIDENCE
                        failure_message = "The trusted knowledge base does not contain sufficient evidence to generate this document."
                        break

                    # Collect citations
                    all_citations = [e.citation for e in retrieved_evidence]
                    current_state = State.REASON

                except Exception as tool_err:
                    logger.error(f"[{task_id}] Knowledge Tool Error: {tool_err}")
                    current_state = State.TOOL_ERROR
                    failure_message = f"Knowledge Tool execution failed: {str(tool_err)}"
                    break

            elif current_state == State.REASON:
                current_state = State.BUILD_STRUCTURED_CONTENT

            elif current_state == State.BUILD_STRUCTURED_CONTENT:
                # Format evidence text for LLM context (passive data wrapper)
                evidence_text_blocks = []
                for idx, ev in enumerate(retrieved_evidence, 1):
                    block = (
                        f"--- EVIDENCE ITEM {idx} ---\n"
                        f"Document ID: {ev.document_id}\n"
                        f"Title: {ev.title}\n"
                        f"Version: {ev.version}\n"
                        f"Section: {ev.section}\n"
                        f"Page: {ev.page}\n"
                        f"Trust Level: {ev.trust_level}\n"
                        f"Content snippet:\n{ev.content}\n"
                    )
                    evidence_text_blocks.append(block)

                full_evidence_prompt = "\n".join(evidence_text_blocks)

                prompt = STRUCTURED_GENERATION_PROMPT.format(
                    objective=request.objective,
                    evidence_text=full_evidence_prompt,
                )

                try:
                    structured_content = self.model_manager.generate_structured(
                        prompt=prompt,
                        schema_cls=StructuredPDFContent,
                        system_prompt=SYSTEM_PROMPT,
                        task_id=task_id,
                    )
                    current_state = State.VERIFY_CONTENT

                except QualityFailureError as q_err:
                    logger.warning(f"[{task_id}] Quality failure in structured generation: {q_err}")
                    if "INSUFFICIENT_EVIDENCE" in str(q_err):
                        current_state = State.INSUFFICIENT_EVIDENCE
                        failure_message = "The trusted knowledge base does not contain sufficient evidence for the requested specification."
                        break

                    reasoning_retry_count += 1
                    if reasoning_retry_count > StateMachineConfig.MAX_REASONING_RETRIES:
                        current_state = State.INSUFFICIENT_EVIDENCE
                        failure_message = "Failed to synthesize grounded structured content after maximum retries."
                        break

                    # Retry evidence retrieval with broader query
                    search_query = f"{request.objective} detail"
                    current_state = State.RETRIEVE_EVIDENCE

                except InfrastructureError as infra_err:
                    # LLM endpoints are offline — fall back to direct evidence synthesis
                    logger.warning(
                        f"[{task_id}] LLM Infrastructure Error: {infra_err}. "
                        f"Falling back to direct evidence synthesis (no LLM reasoning)."
                    )
                    structured_content = _synthesize_from_evidence(
                        objective=request.objective,
                        evidence=retrieved_evidence,
                    )
                    used_direct_synthesis = True
                    # Skip verification for direct synthesis (content is deterministic from evidence)
                    current_state = State.GENERATE_PDF

            elif current_state == State.VERIFY_CONTENT:
                if not structured_content:
                    current_state = State.BUILD_STRUCTURED_CONTENT
                    continue

                v_res = self.verifier.verify(
                    content=structured_content,
                    retrieved_evidence=retrieved_evidence,
                )

                if not v_res.is_valid:
                    logger.warning(
                        f"[{task_id}] Content Verification Failed with {len(v_res.unsupported_claims)} unsupported claims: {v_res.unsupported_claims}"
                    )
                    reasoning_retry_count += 1
                    if reasoning_retry_count > StateMachineConfig.MAX_REASONING_RETRIES:
                        current_state = State.INSUFFICIENT_EVIDENCE
                        failure_message = (
                            "Generated content contained unsupported claims that failed deterministic verification: "
                            + "; ".join(v_res.unsupported_claims[:2])
                        )
                        break

                    # Retry retrieval/reasoning
                    current_state = State.RETRIEVE_EVIDENCE
                else:
                    logger.info(f"[{task_id}] Content Verification PASSED cleanly.")
                    current_state = State.GENERATE_PDF

            elif current_state == State.GENERATE_PDF:
                if not structured_content:
                    current_state = State.BUILD_STRUCTURED_CONTENT
                    continue

                try:
                    model_label = "Direct Evidence Synthesis" if used_direct_synthesis else self.model_manager.get_active_model()
                    pdf_bytes = self.pdf_generator.generate(
                        content=structured_content,
                        task_id=task_id,
                        model_name=model_label,
                        fallback_used=self.model_manager.fallback_used or used_direct_synthesis,
                    )
                    current_state = State.VERIFY_PDF

                except Exception as pdf_err:
                    logger.error(f"[{task_id}] PDF Generation Error: {pdf_err}")
                    current_state = State.PDF_GENERATION_FAILED
                    failure_message = f"PDF rendering failed: {str(pdf_err)}"
                    break

            elif current_state == State.VERIFY_PDF:
                if not pdf_bytes:
                    current_state = State.GENERATE_PDF
                    continue

                valid_pdf, err_msg = self.pdf_validator.validate(
                    pdf_bytes=pdf_bytes,
                    expected_title=structured_content.title if structured_content else None,
                )

                if not valid_pdf:
                    logger.error(f"[{task_id}] PDF Validation Failed: {err_msg}")
                    current_state = State.PDF_GENERATION_FAILED
                    failure_message = f"Generated PDF failed PyMuPDF validation: {err_msg}"
                    break

                # Store artifact in MinIO / ObjectStorage
                safe_objective = "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in request.objective[:30])
                filename = f"{task_id}_{safe_objective.replace(' ', '_')}.pdf"
                try:
                    storage_uri = minio_client.upload_raw_document(
                        file_bytes=pdf_bytes,
                        filename=filename,
                        document_id=task_id,
                        bucket_name="trusted",
                    )
                    artifact_metadata = ArtifactMetadata(
                        filename=filename,
                        content_type="application/pdf",
                        storage_uri=storage_uri,
                        file_size_bytes=len(pdf_bytes),
                        bucket="trusted",
                    )
                    current_state = State.COMPLETE

                except Exception as store_err:
                    logger.error(f"[{task_id}] MinIO artifact storage error: {store_err}")
                    # Fall back to local artifact reference
                    artifact_metadata = ArtifactMetadata(
                        filename=filename,
                        content_type="application/pdf",
                        storage_uri=f"file:///tmp/{filename}",
                        file_size_bytes=len(pdf_bytes),
                    )
                    current_state = State.COMPLETE

        # Construct AgentTaskResult
        model_label = "Direct Evidence Synthesis" if used_direct_synthesis else self.model_manager.get_active_model()
        synthesis_note = " (Generated via direct evidence synthesis — no LLM reasoning)" if used_direct_synthesis else ""

        return AgentTaskResult(
            task_id=task_id,
            status=current_state.value,
            result_type="PDF",
            artifact=artifact_metadata,
            model=model_label,
            fallback_used=self.model_manager.fallback_used or used_direct_synthesis,
            citations=all_citations,
            message=(
                failure_message
                if failure_message
                else f"Task completed successfully with state '{current_state.value}'.{synthesis_note}"
            ),
            structured_content=structured_content,
        )

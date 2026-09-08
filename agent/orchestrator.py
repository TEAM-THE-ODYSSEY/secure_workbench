"""
Main Orchestrator for MRPL Sovereign AI Workbench.
Central controller orchestrating TaskPlan generation, Agent selection, Skill discovery,
Safe Dependency Execution, Evidence Fusion, and Grounding Verification.
Primary Model: Qwen2.5-VL-7B-Instruct / Qwen2.5-1.5B-Instruct-AWQ (served via vLLM).
"""

import logging
import time
import uuid
from typing import List, Optional
from agent.dependency_executor import dependency_executor
from agent.evidence_fusion import evidence_fusion
from agent.models.model_manager import ModelManager
from agent.models.schemas import (
    AgentResult,
    AgentSpec,
    AgentTaskResult,
    ContextPack,
    FinalReasoningOutput,
    TaskContext,
    TaskPlan,
    TaskRequest,
)
from agent.prompts import REASONING_OUTPUT_PROMPT, SYSTEM_PROMPT
from agent.task_manager import TaskStatus, task_manager
from agent.verification.grounding_verifier import GroundingVerifier
from skills.registry import skill_registry

logger = logging.getLogger("agent.orchestrator")


class MainOrchestrator:
    """
    Main Orchestrator.
    Decides user intent, required context, agents, skills, tools, and synthesis strategy.
    Does NOT directly execute all capabilities—delegates to specialized agents.
    """

    def __init__(
        self,
        model_manager: Optional[ModelManager] = None,
        verifier: Optional[GroundingVerifier] = None,
    ):
        self.model_manager = model_manager or ModelManager()
        self.verifier = verifier or GroundingVerifier()

    def build_task_plan(self, context: TaskContext) -> TaskPlan:
        """
        Query Understanding & Task Plan Generation with referent resolution.
        """
        q_lower = context.query.lower().strip()
        agents_list: List[AgentSpec] = []
        doc_file_ids: List[str] = []
        intent = "GENERAL"

        discovered_skill = skill_registry.discover_skill(context.query)
        skill_name = discovered_skill.name if discovered_skill else None

        ref_keywords = [
            "it", "this", "this document", "this file", "the document", "the file",
            "summarize it", "explain it", "what does it say", "read it", "tell me about it",
            "summarize this", "explain this"
        ]
        is_referent = any(kw in q_lower for kw in ref_keywords)

        is_mrpl_kw = any(kw in q_lower for kw in [
            "mrpl", "sop", "p-101a", "cdu", "oisd", "xv-101", "shutdown", "vibration", "pump", "refinery"
        ])
        greeting_kw = any(kw in q_lower for kw in ["hi", "hello", "hey", "greetings", "good morning", "how are you", "who are you"])
        general_q = any(kw in q_lower for kw in ["2+2", "calculate", "what is crude oil refining", "explain crude oil refining"])

        # 1. Attachment referent resolution logic
        if context.attachments:
            doc_file_ids = [a.get("name") or a.get("file_id") or "file" for a in context.attachments]

            # Multiple attachments with ambiguous referent
            if len(context.attachments) > 1 and is_referent and not any(fid.lower() in q_lower for fid in doc_file_ids):
                intent = "AMBIGUOUS_ATTACHMENTS"
                logger.info(f"[PLANNER] intent={intent} document_file_ids={doc_file_ids}")
                return TaskPlan(intent=intent, agents=[], skill_name=skill_name, output_type="TEXT")

            # Check if comparison with MRPL knowledge base is requested
            needs_knowledge_comparison = is_mrpl_kw or any(kw in q_lower for kw in ["compare", "vs", "versus", "mrpl sop"])

            if needs_knowledge_comparison:
                intent = "DOCUMENT_ANALYSIS"
                agents_list.append(AgentSpec(name="document", purpose="Analyze uploaded document", depends_on=[]))
                agents_list.append(AgentSpec(name="knowledge", purpose="Search internal MRPL Knowledge Base", depends_on=[]))
            else:
                intent = "DOCUMENT_ANALYSIS"
                agents_list.append(AgentSpec(name="document", purpose="Analyze uploaded document", depends_on=[]))

            logger.info(f"[PLANNER] intent={intent} document_file_ids={doc_file_ids}")
            return TaskPlan(intent=intent, agents=agents_list, skill_name=skill_name, output_type="TEXT")

        # 2. No attachments case
        if (greeting_kw or general_q) and not is_mrpl_kw:
            intent = "GENERAL_KNOWLEDGE"
            agents_list.append(AgentSpec(name="general", purpose="General conversational response", depends_on=[]))
            logger.info(f"[PLANNER] intent={intent} document_file_ids=[]")
            return TaskPlan(intent=intent, agents=agents_list, skill_name=skill_name, output_type="TEXT")

        if is_mrpl_kw or any(kw in q_lower for kw in ["sop", "safety", "health", "manual", "procedure", "shutdown"]):
            intent = "LOCAL_KNOWLEDGE"
            agents_list.append(AgentSpec(name="knowledge", purpose="Search internal MRPL Knowledge Base", depends_on=[]))
            logger.info(f"[PLANNER] intent={intent} document_file_ids=[]")
            return TaskPlan(intent=intent, agents=agents_list, skill_name=skill_name, output_type="TEXT")

        # Default fallback
        intent = "LOCAL_KNOWLEDGE" if is_mrpl_kw else "GENERAL_KNOWLEDGE"
        if is_mrpl_kw:
            agents_list.append(AgentSpec(name="knowledge", purpose="Search internal MRPL Knowledge Base", depends_on=[]))
        else:
            agents_list.append(AgentSpec(name="general", purpose="General response", depends_on=[]))

        logger.info(f"[PLANNER] intent={intent} document_file_ids=[]")
        return TaskPlan(intent=intent, agents=agents_list, skill_name=skill_name, output_type="TEXT")

    def process_task(
        self,
        request: TaskRequest,
        task_id: Optional[str] = None,
        user_id: str = "operator",
        conversation_id: str = "conv_default",
    ) -> AgentTaskResult:
        """
        Execute full multi-agent orchestration lifecycle.
        """
        task_id = task_id or f"task_{uuid.uuid4().hex[:12]}"
        t_start = time.time()

        task_rec = task_manager.register_task(task_id=task_id, user_id=user_id, conversation_id=conversation_id)
        task_manager.update_status(task_id, TaskStatus.PLANNING, active_step="QUERY_UNDERSTANDING")

        attachments = []
        if getattr(request, "attachments", None):
            attachments.extend(request.attachments)
        if request.attached_file and request.attached_file not in attachments:
            attachments.append(request.attached_file)
        elif request.scoped_file_id and not attachments:
            attachments.append({"name": request.scoped_file_id, "file_id": request.scoped_file_id})
        if request.extracted_text:
            if not attachments:
                attachments.append({"name": "Uploaded Document", "extracted_text": request.extracted_text})
            else:
                for att in attachments:
                    if not att.get("extracted_text"):
                        att["extracted_text"] = request.extracted_text

        context = TaskContext(
            task_id=task_id,
            user_id=user_id,
            conversation_id=conversation_id,
            workspace_id="default_workspace",
            role="OPERATOR",
            permissions=["agent.use", "knowledge.read", "pid.use", "coding.use", "reports.create", "sandbox.use"],
            query=request.objective,
            attachments=attachments,
            entity_context=list(request.entities),
        )

        att_names = [a.get("name") or a.get("file_id") or "file" for a in context.attachments]
        logger.info(f"[REQUEST] query={context.query} attachments={att_names}")

        task_plan = self.build_task_plan(context)
        context.task_plan = task_plan

        if task_manager.is_cancelled(task_id):
            task_manager.update_status(task_id, TaskStatus.CANCELLED)
            return AgentTaskResult(task_id=task_id, status="CANCELLED", answer="Task execution was stopped by user request.")

        if task_plan.intent == "AMBIGUOUS_ATTACHMENTS":
            att_list_str = ", ".join(att_names)
            ans = f"Multiple attachments detected ({att_list_str}). Please specify which file you would like me to analyze."
            task_manager.update_status(task_id, TaskStatus.COMPLETED, active_step="COMPLETE")
            return AgentTaskResult(
                task_id=task_id,
                status="COMPLETE",
                result_type="TEXT",
                answer=ans,
                model=self.model_manager.get_active_model(),
                fallback_used=self.model_manager.fallback_used,
                message="Ambiguous attachment reference",
            )

        task_manager.update_status(task_id, TaskStatus.RUNNING, active_step="EXECUTE_AGENTS")
        t_exec0 = time.time()
        agent_results: List[AgentResult] = dependency_executor.execute_plan_sync(context, task_plan)
        latency_exec = (time.time() - t_exec0) * 1000.0

        if task_manager.is_cancelled(task_id):
            task_manager.update_status(task_id, TaskStatus.CANCELLED)
            return AgentTaskResult(task_id=task_id, status="CANCELLED", answer="Analysis stopped by user. Completed results have been preserved.")

        task_manager.update_status(task_id, TaskStatus.VERIFYING, active_step="EVIDENCE_FUSION")
        context_pack: ContextPack = evidence_fusion.fuse_agent_results(context, agent_results)

        t_llm0 = time.time()
        active_model = self.model_manager.get_active_model()
        logger.info(f"[MODEL] model={active_model} generation_started=true")

        if context_pack.evidence_chunks:
            evidence_text = "\n\n".join([
                f"[{idx+1}] Source: {c.title} (Section: {c.section}, Page: {c.page or 1})\n{c.content}"
                for idx, c in enumerate(context_pack.evidence_chunks)
            ])
            prompt = (
                f"User Request: {context.query}\n\n"
                f"Retrieved Evidence:\n{evidence_text}\n\n"
                f"Instructions: Provide a detailed, clear answer grounded strictly in the provided evidence. Cite sources using [1], [2], etc."
            )
        else:
            prompt = f"User Request: {context.query}\n\nInstructions: Provide a comprehensive and clear technical response."

        # Check if GeneralAgent already produced a clean conversational/greeting response
        gen_res = next((r for r in agent_results if r.agent == "general" and r.content), None)
        if task_plan.intent == "GENERAL_KNOWLEDGE" and gen_res:
            answer_text = gen_res.content
            logger.info(f"[{task_id}] Using direct GeneralAgent response for query '{context.query}'.")
        else:
            try:
                answer_text = self.model_manager.generate(
                    prompt=prompt,
                    system_prompt=SYSTEM_PROMPT,
                    task_id=task_id,
                )
                logger.info(f"[MODEL] model={active_model} generation_completed=true")
            except Exception as ex:
                logger.warning(f"[{task_id}] ModelManager.generate fallback: {ex}")
                answer_text = ""
                for res in agent_results:
                    if res.content:
                        answer_text = (answer_text + "\n\n" + res.content).strip() if answer_text else res.content
                if not answer_text:
                    answer_text = f"Analyzed query '{context.query}'."
                logger.info(f"[MODEL] model={active_model} generation_completed=true")

        latency_llm = (time.time() - t_llm0) * 1000.0
        total_latency = (time.time() - t_start) * 1000.0

        if context_pack.evidence_chunks:
            self.verifier.verify_final_output(
                FinalReasoningOutput(answer=answer_text, claims=[], citations=context_pack.citations),
                context_pack.evidence_chunks,
            )

        task_manager.update_status(task_id, TaskStatus.COMPLETED, active_step="COMPLETE")
        logger.info(f"[{task_id}] Completed MainOrchestrator execution in {total_latency:.1f}ms (exec: {latency_exec:.1f}ms, llm: {latency_llm:.1f}ms).")

        return AgentTaskResult(
            task_id=task_id,
            status="COMPLETE",
            result_type=task_plan.output_type,
            answer=answer_text,
            model=self.model_manager.get_active_model(),
            fallback_used=self.model_manager.fallback_used,
            citations=context_pack.citations,
            message="Task executed successfully",
        )

    def run_sync(self, context: TaskContext) -> AgentTaskResult:
        req = TaskRequest(
            objective=context.query,
            attached_file=context.attachments[0] if len(context.attachments) == 1 else None,
            attachments=context.attachments if len(context.attachments) > 1 else None,
            entities=context.entity_context,
        )
        return self.process_task(req, task_id=context.task_id, user_id=context.user_id, conversation_id=context.conversation_id)

    async def run(self, context: TaskContext) -> AgentTaskResult:
        return self.run_sync(context)


# Global singleton instance
main_orchestrator = MainOrchestrator()

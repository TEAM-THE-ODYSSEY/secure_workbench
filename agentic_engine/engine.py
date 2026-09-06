from __future__ import annotations

from .agents.coding import CodingAgent
from .agents.mathematical import MathematicalAgent
from .agents.reasoning import ReasoningAgent
from .code_runner import CodingWorkflow
from .config import Settings
from .document_output import DocumentOutput
from .extractors import extract
from .guardrails.input_guard import InputGuard
from .knowledge import KnowledgeRetriever
from .llm import OllamaClient
from .models.selector import ModelSelector
from .orchestrator.planner import Planner
from .sandbox import DockerSandbox
from .session_store import SessionStore
from .state.schema import AgentState, ValidationState
from .validators import get_validator


class Orchestrator:
    """Central brain for the generic Agentic AI Workbench.

    The planner decides what to call. State records what happened. Agents do
    the work. Validators decide whether the result is acceptable. A failed
    validation returns control to the orchestrator for bounded re-planning.
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or Settings()
        self.store = SessionStore(self.settings.db_path)
        self.llm = OllamaClient(self.settings)
        self.guard = InputGuard()
        self.planner = Planner(self.llm)
        self.selector = ModelSelector()
        self.retriever = KnowledgeRetriever()
        self.sandbox = DockerSandbox()
        self.doc_output = DocumentOutput()

        self.agents = {
            "reasoning": ReasoningAgent(self.llm),
            "mathematical": MathematicalAgent(self.llm),
            "coding": CodingAgent(self.llm),
        }

    def new_chat(self):
        return self.store.create_chat()

    @staticmethod
    def _format_context(file_text: str, retrieved: list[dict]) -> str:
        parts = []
        if file_text:
            parts.append("FILE CONTENT:\n" + file_text)
        if retrieved:
            parts.append("RETRIEVED COMPANY CONTEXT:\n" + "\n".join(
                f"- {x.get('text', '')}" for x in retrieved
            ))
        return "\n\n".join(parts)

    @staticmethod
    def _retrieval_requested(state: AgentState) -> bool:
        return state.plan.retrieval

    def _create_output(self, state: AgentState):
        if state.plan.output_type == "text":
            return None
        try:
            return self.doc_output.create(
                filename="agent_output",
                content=state.answer,
                fmt=state.plan.output_type,
            )
        except Exception as exc:
            state.error = f"Output generation failed: {exc}"
            return None

    def _validate(self, state: AgentState):
        validator = get_validator(state.plan.validation_type)
        result = validator.validate(
            state.answer,
            execution=state.execution_result,
            user_request=state.user_request,
        )
        state.validation = ValidationState(result.valid, result.reason, result.details or {})

    def _run_agent(self, state: AgentState):
        agent_name = state.plan.agent
        model = state.selected_model
        metadata = {"history": state.history, "state": state.to_dict()}

        if agent_name == "coding":
            workflow = CodingWorkflow(self.llm, sandbox=self.sandbox, max_attempts=1)
            result = workflow.run(state.user_request, self._context(state), model)
            state.answer = result.final_explanation
            state.execution_result = result.execution
            state.current_step = "validation"
            return

        agent = self.agents[agent_name]
        state.answer = agent.run(
            user_text=state.user_request or "Analyze the supplied file and provide the most useful answer.",
            context=self._context(state),
            model=model,
            metadata=metadata,
        )
        state.current_step = "validation"

    def _context(self, state: AgentState) -> str:
        return self._format_context(
            state.file_content[:self.settings.max_context_chars],
            state.retrieved_context,
        )

    def _replan_after_failure(self, state: AgentState):
        feedback = state.validation.reason
        state.user_request = (
            f"{state.user_request}\n\nPrevious attempt failed validation.\n"
            f"Validator feedback: {feedback}\nProduce a corrected result."
        )
        # Keep the original task family unless a genuine planning error is detected.
        state.current_step = "replan"

    def run(self, chat_id: str, message: str = "", file_path: str | None = None):
        if not self.store.exists(chat_id):
            raise ValueError(f"Unknown chat ID: {chat_id}")

        allowed, reason = self.guard.check(message, file_path)
        if not allowed:
            self.store.add(chat_id, "system", f"Request blocked before LLM: {reason}", {"blocked": True})
            return {"chat_id": chat_id, "blocked": True, "task": "blocked", "answer": "Request blocked by pre-LLM guardrails."}

        file_content = ""
        if file_path:
            extracted = extract(file_path)
            file_content = extracted.get("text", "")

        state = AgentState(
            chat_id=chat_id,
            user_request=message,
            file_path=file_path,
            file_content=file_content,
            history=self.store.history(chat_id, self.settings.max_history),
        )
        state.current_step = "planning"

        state.plan = self.planner.plan(
            message,
            context_chars=len(file_content),
            has_file=bool(file_path),
        )

        if state.plan.retrieval:
            state.retrieved_context = self.retriever.search(message, limit=5)

        state.plan = self.planner.plan(
            message,
            context_chars=len(self._context(state)),
            has_file=bool(file_path),
        )

        model = self.selector.select(
            state.plan.task_type,
            state.plan.complexity,
            required_context=len(self._context(state)),
        )
        state.selected_model = model.name
        state.model_parameters = model.parameters

        self.store.add(chat_id, "user", message or "[file upload]", {"plan": state.plan.to_dict(), "model": model.name})

        for iteration in range(1, state.plan.max_iterations + 1):
            state.iteration = iteration
            state.current_step = "agent_execution"
            try:
                self._run_agent(state)
                self._validate(state)
                if state.validation.valid:
                    state.status = "completed"
                    break
                self._replan_after_failure(state)
            except Exception as exc:
                state.error = str(exc)
                state.validation = ValidationState(False, str(exc), {})
                if iteration < state.plan.max_iterations:
                    self._replan_after_failure(state)
                else:
                    state.status = "failed"

        if not state.validation.valid:
            state.status = "failed"
            if state.answer:
                state.answer += f"\n\nValidation status: FAILED. {state.validation.reason}"
            else:
                state.answer = f"The task could not be completed.\n\nValidation status: FAILED. {state.validation.reason}"
        else:
            state.output_file = self._create_output(state)
            if state.output_file:
                state.answer += f"\n\nOUTPUT FILE: {state.output_file}"

        self.store.add(chat_id, "assistant", state.answer, {
            "plan": state.plan.to_dict(),
            "model": state.selected_model,
            "validation": state.validation.to_dict(),
            "state": state.to_dict(),
        })

        return {
            "chat_id": chat_id,
            "blocked": False,
            "task": state.plan.task_type,
            "complexity": state.plan.complexity,
            "model": state.selected_model,
            "parameters": state.model_parameters,
            "plan": state.plan.to_dict(),
            "answer": state.answer,
            "validated": state.validation.valid,
            "output_file": state.output_file,
            "status": state.status,
        }

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List, Optional

from .budgets import BudgetTracker, ExecutionBudget
from .context import ScopedContext
from .state import ExecutionState, StateTracker
from ..models.registry import ModelProfile
from ..models.selector import ModelSelector
from ..orchestration.execution_plan import ExecutionPlan
from ..validators.base import ValidationResult

logger = logging.getLogger("agentic_engine.executor")


class ExecutionCoordinator:
    """Executes an ExecutionPlan with formal state tracking, budget enforcement,
    and distinct retry, repair, and replan workflows.
    """

    def __init__(
        self,
        agents: Dict[str, Any],
        model_selector: ModelSelector,
        validator_runner_fn: Callable[[str, Any, str, Any], ValidationResult],
        doc_output_fn: Optional[Callable[[str, str, str], str]] = None,
    ):
        self.agents = agents
        self.model_selector = model_selector
        self.validator_runner_fn = validator_runner_fn
        self.doc_output_fn = doc_output_fn

    def execute(
        self,
        plan: ExecutionPlan,
        context: ScopedContext,
        replan_callback_fn: Optional[Callable[[str, str], ExecutionPlan]] = None,
    ) -> Dict[str, Any]:
        state_tracker = StateTracker(ExecutionState.PLANNED)
        budget = ExecutionBudget.for_complexity(plan.complexity)
        if plan.max_iterations > budget.max_iterations:
            budget.max_iterations = plan.max_iterations
        if plan.max_retries > budget.max_retries:
            budget.max_retries = plan.max_retries
        if plan.max_tool_calls > budget.max_tool_calls:
            budget.max_tool_calls = plan.max_tool_calls
        tracker = BudgetTracker(budget)

        # 1. State: AUTHORIZED
        state_tracker.transition_to(ExecutionState.AUTHORIZED, "Execution plan approved by policy engine")

        # 2. Select Model (Capability-Safe & Resource-Aware)
        state_tracker.transition_to(ExecutionState.MODEL_SELECTED, "Selecting qualified model")
        selected_model: ModelProfile = self.model_selector.select(
            task_type=plan.task_type,
            complexity=plan.complexity,
            required_context=len(context.file_content or "") + len(context.task_context),
        )

        active_agent_name = plan.agent
        final_answer = ""
        execution_result = None
        validation_result: Optional[ValidationResult] = None
        retry_count = 0
        replan_count = 0
        model_switch_count = 0
        evidence_collected: List[Dict[str, Any]] = []
        warnings: List[str] = []

        # 3. Execution Lifecycle Loop
        for iteration in range(1, plan.max_iterations + 1):
            tracker.record_iteration()
            tracker.check_timeout()
            state_tracker.transition_to(ExecutionState.RUNNING, f"Executing iteration {iteration}")

            # Prepare Agent-specific scoped context
            scoped_agent_context = context.for_agent(active_agent_name)
            agent = self.agents.get(active_agent_name, self.agents.get("reasoning"))

            if not agent:
                state_tracker.transition_to(ExecutionState.FAILED, f"Agent '{active_agent_name}' not found")
                return self._build_response(
                    status="failed",
                    plan=plan,
                    agent=active_agent_name,
                    model=selected_model.name,
                    answer="Execution halted: Designated agent is unavailable.",
                    error=f"Agent '{active_agent_name}' not found",
                    tracker=tracker,
                    evidence=evidence_collected,
                    warnings=warnings,
                )

            metadata = {
                "plan": plan.to_dict(),
                "iteration": iteration,
                "file_path": context.file_path,
                "request_id": context.request_id,
            }

            try:
                # Run Agent execution
                if hasattr(agent, "execute_task"):
                    res = agent.execute_task(
                        directive=context.task_context,
                        context=scoped_agent_context,
                        model=selected_model.name,
                        metadata=metadata,
                    )
                    final_answer = res.get("answer", "")
                    execution_result = res.get("execution_result")
                    if "evidence" in res:
                        evidence_collected.extend(res["evidence"])
                    if "warnings" in res:
                        warnings.extend(res["warnings"])
                else:
                    final_answer = agent.run(
                        user_text=context.task_context or "Analyze the provided input and produce a structured answer.",
                        context=scoped_agent_context,
                        model=selected_model.name,
                        metadata=metadata,
                    )

                # Validation Phase
                state_tracker.transition_to(ExecutionState.VALIDATING, "Running validator chain")
                validation_result = self.validator_runner_fn(
                    plan.validator_chain if plan.validator_chain else ["text"],
                    final_answer,
                    context.task_context,
                    execution_result,
                )

                if validation_result.valid:
                    state_tracker.transition_to(ExecutionState.COMPLETED, "All validators passed")
                    break

                # Validation Failed: Differentiate REPAIR (Retry) vs REPLAN (Section 17)
                if iteration < plan.max_iterations:
                    retry_count += 1
                    tracker.record_retry()
                    state_tracker.transition_to(
                        ExecutionState.REPAIRING,
                        f"Validator feedback: {validation_result.reason}. Attempting repair."
                    )
                    context.previous_attempt_context = (
                        f"Previous output: {final_answer[:500]}\n"
                        f"Validator failure reason: {validation_result.reason}"
                    )
                else:
                    # Exceeded iterations: check if Replan is possible
                    if replan_callback_fn and replan_count < plan.max_retries:
                        replan_count += 1
                        state_tracker.transition_to(ExecutionState.REPLANNING, "Triggering formal Planner re-evaluation")
                        new_plan = replan_callback_fn(context.task_context, validation_result.reason)
                        plan = new_plan
                        state_tracker.transition_to(ExecutionState.RUNNING, "Executing revised plan")
                    else:
                        state_tracker.transition_to(ExecutionState.FAILED, "Validation criteria could not be satisfied")

            except Exception as exc:
                logger.error(f"Execution step failed: {exc}", exc_info=True)
                warnings.append(str(exc))
                if iteration >= plan.max_iterations:
                    state_tracker.transition_to(ExecutionState.FAILED, str(exc))
                    return self._build_response(
                        status="failed",
                        plan=plan,
                        agent=active_agent_name,
                        model=selected_model.name,
                        answer=final_answer or "Execution failed due to unrecoverable errors.",
                        error=str(exc),
                        tracker=tracker,
                        evidence=evidence_collected,
                        warnings=warnings,
                    )

        # 4. Final Output Artifact Creation
        output_file = None
        if execution_result and hasattr(execution_result, "xlsx_path") and execution_result.xlsx_path:
            output_file = execution_result.xlsx_path
        elif self.doc_output_fn and plan.output_type != "text" and final_answer:
            try:
                output_file = self.doc_output_fn("agent_output", final_answer, plan.output_type)
            except Exception as e:
                warnings.append(f"Output artifact generation error: {e}")

        status_str = "success" if (validation_result and validation_result.valid) else "failed"
        if status_str == "success" and warnings:
            status_str = "success_with_warnings"

        return self._build_response(
            status=status_str,
            plan=plan,
            agent=active_agent_name,
            model=selected_model.name,
            answer=final_answer,
            validation=validation_result.to_dict() if validation_result else {},
            output_file=output_file,
            tracker=tracker,
            evidence=evidence_collected,
            warnings=warnings,
            retry_count=retry_count,
            replan_count=replan_count,
            model_switch_count=model_switch_count,
        )

    @staticmethod
    def _build_response(
        status: str,
        plan: ExecutionPlan,
        agent: str,
        model: str,
        answer: str,
        tracker: BudgetTracker,
        validation: Optional[Dict[str, Any]] = None,
        output_file: Optional[str] = None,
        error: Optional[str] = None,
        evidence: Optional[List[Dict[str, Any]]] = None,
        warnings: Optional[List[str]] = None,
        retry_count: int = 0,
        replan_count: int = 0,
        model_switch_count: int = 0,
    ) -> Dict[str, Any]:
        return {
            "status": status,
            "task_type": plan.task_type,
            "complexity": plan.complexity,
            "capabilities": plan.capabilities,
            "agent": agent,
            "model": model,
            "tools": plan.tools,
            "validation": validation or {},
            "evidence": evidence or [],
            "warnings": warnings or [],
            "artifacts": {"file": output_file} if output_file else {},
            "latency": {"total_ms": round(tracker.elapsed_seconds() * 1000, 2)},
            "usage": {
                "iterations": tracker.iterations_used,
                "retries": retry_count,
                "replans": replan_count,
                "model_switches": model_switch_count,
                "tool_calls": tracker.tool_calls_used,
            },
            "answer": answer,
            "output_file": output_file,
            "error": error,
        }

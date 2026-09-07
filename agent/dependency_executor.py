"""
Safe Dependency-Aware Concurrency Executor for MRPL Sovereign AI Workbench.
Executes independent agents concurrently when safe and serializes dependent or GPU-heavy agents.
"""

import asyncio
import logging
from typing import Dict, List, Set
from agent.models.schemas import AgentResult, AgentSpec, TaskContext, TaskPlan
from agent.registry.agent_registry import agent_registry
from agent.task_manager import task_manager

logger = logging.getLogger("agent.dependency_executor")


class DependencyExecutor:
    """
    Dependency & Resource-Aware Task Plan Scheduler.
    Executes independent tasks concurrently and dependent tasks sequentially.
    """

    async def execute_plan_async(self, context: TaskContext, plan: TaskPlan) -> List[AgentResult]:
        """
        Execute TaskPlan agents according to dependency graph and safe concurrency rules.
        """
        results: List[AgentResult] = []
        completed_agents: Set[str] = set()
        agent_outputs: Dict[str, AgentResult] = {}

        if not plan.agents:
            logger.info(f"[{context.task_id}] TaskPlan has 0 agent steps.")
            return results

        specs_to_run = list(plan.agents)

        while specs_to_run:
            # Check for user task cancellation signal
            if task_manager.is_cancelled(context.task_id):
                logger.warning(f"[{context.task_id}] Task cancellation detected during dependency execution.")
                break

            # Find specs whose dependencies are satisfied
            ready_specs: List[AgentSpec] = [
                s for s in specs_to_run
                if all(dep in completed_agents for dep in s.depends_on)
            ]

            if not ready_specs:
                # Cycle detected or unmet dependency
                logger.error(f"[{context.task_id}] Deadlock/unmet dependency in TaskPlan: {[s.name for s in specs_to_run]}")
                break

            # Group ready specs: Independent safe agents vs GPU-heavy agents
            # Note: GPU-heavy agents (e.g. LLM-based general reasoning) run sequentially to prevent VRAM fragmentation
            cpu_ready = [s for s in ready_specs if s.name in ("document", "knowledge", "pid")]
            gpu_ready = [s for s in ready_specs if s.name in ("general", "coding", "report")]

            # 1. Run safe CPU/IO independent agents in parallel via asyncio.gather()
            if cpu_ready:
                logger.info(f"[{context.task_id}] Executing independent agents concurrently: {[s.name for s in cpu_ready]}")
                tasks = [
                    asyncio.to_thread(agent_registry.execute_agent, s.name, context)
                    for s in cpu_ready
                ]
                gathered_results = await asyncio.gather(*tasks, return_exceptions=True)

                for spec, res in zip(cpu_ready, gathered_results):
                    specs_to_run.remove(spec)
                    completed_agents.add(spec.name)

                    if isinstance(res, Exception):
                        logger.error(f"[{context.task_id}] Agent '{spec.name}' failed with exception: {res}")
                        err_res = AgentResult(agent=spec.name, status="failure", errors=[str(res)])
                        results.append(err_res)
                        agent_outputs[spec.name] = err_res
                    else:
                        results.append(res)
                        agent_outputs[spec.name] = res

            # 2. Run GPU-heavy or serial agents sequentially
            elif gpu_ready:
                spec = gpu_ready[0]
                logger.info(f"[{context.task_id}] Executing serial agent: '{spec.name}'")

                # Pass upstream output content to context metadata for dependent agent
                upstream_evidence = []
                for dep_name in spec.depends_on:
                    if dep_name in agent_outputs and agent_outputs[dep_name].evidence:
                        upstream_evidence.extend(agent_outputs[dep_name].evidence)
                if upstream_evidence:
                    context.retrieved_evidence.extend(upstream_evidence)

                res = await asyncio.to_thread(agent_registry.execute_agent, spec.name, context)
                specs_to_run.remove(spec)
                completed_agents.add(spec.name)
                results.append(res)
                agent_outputs[spec.name] = res

        return results

    def execute_plan_sync(self, context: TaskContext, plan: TaskPlan) -> List[AgentResult]:
        """Synchronous wrapper for execute_plan_async."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(lambda: asyncio.run(self.execute_plan_async(context, plan)))
                return future.result()
        else:
            return asyncio.run(self.execute_plan_async(context, plan))


# Global singleton instance
dependency_executor = DependencyExecutor()

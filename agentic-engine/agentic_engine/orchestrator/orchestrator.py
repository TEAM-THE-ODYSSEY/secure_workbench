"""
Orchestrator
-------------
For this pass there is NO automatic task router yet (by design — see
README). The orchestrator dispatches purely on `Task.agent_type`,
which the caller sets explicitly. This keeps the engine fully usable
standalone; a TaskRouter can be added later as a thin layer that just
sets `agent_type` before calling `Orchestrator.run_task`, with no
change needed here.
"""

from __future__ import annotations

from typing import Dict

from ..agents.base_agent import BaseAgent
from ..schemas.response import AgentResponse
from ..schemas.task import Task, TaskStatus
from .task_state import TaskStateStore


class UnknownAgentError(ValueError):
    pass


class Orchestrator:
    def __init__(self, agents: Dict[str, BaseAgent], state_store: TaskStateStore | None = None):
        """
        agents: e.g. {"reasoning": ReasoningAgent(...), "mathematical": MathematicalAgent(...)}
        """
        self.agents = agents
        self.state = state_store or TaskStateStore()

    def register_agent(self, name: str, agent: BaseAgent) -> None:
        self.agents[name] = agent

    def run_task(self, task: Task) -> AgentResponse:
        self.state.register(task)

        agent = self.agents.get(task.agent_type)
        if agent is None:
            response = AgentResponse(
                task_id=task.id,
                agent_name=task.agent_type,
                status=TaskStatus.FAILED,
                content="",
                error=(
                    f"No agent registered for agent_type={task.agent_type!r}. "
                    f"Available: {list(self.agents.keys())}"
                ),
            )
            self.state.record_result(task.id, response)
            return response

        self.state.mark_running(task.id)
        response = agent.run(task)
        self.state.record_result(task.id, response)
        return response

from agentic_engine.orchestrator.orchestrator import Orchestrator
from agentic_engine.schemas.task import Task, TaskStatus


class StubAgent:
    def __init__(self, name):
        self.name = name

    def run(self, task):
        from agentic_engine.schemas.response import AgentResponse

        return AgentResponse(
            task_id=task.id,
            agent_name=self.name,
            status=TaskStatus.SUCCESS,
            content=f"handled by {self.name}",
        )


def test_dispatches_to_correct_agent():
    orchestrator = Orchestrator(agents={"reasoning": StubAgent("reasoning")})
    task = Task(input_text="hello", agent_type="reasoning")

    response = orchestrator.run_task(task)

    assert response.status == TaskStatus.SUCCESS
    assert response.content == "handled by reasoning"
    assert orchestrator.state.get_task(task.id).status == TaskStatus.SUCCESS


def test_unknown_agent_type_fails_cleanly():
    orchestrator = Orchestrator(agents={"reasoning": StubAgent("reasoning")})
    task = Task(input_text="hello", agent_type="vision")

    response = orchestrator.run_task(task)

    assert response.status == TaskStatus.FAILED
    assert "vision" in response.error
    assert "reasoning" in response.error

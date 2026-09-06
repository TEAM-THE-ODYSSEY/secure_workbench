"""
These tests use a FakeGateway instead of a real Ollama daemon, so the
test suite runs anywhere with no local model required. They verify the
agent's control flow (code-block parsing, loop termination, tool
wiring) — not model quality, which can't be unit tested anyway.
"""

from agentic_engine.agents.reasoning_agent import ReasoningAgent
from agentic_engine.schemas.task import Task, TaskStatus


class FakeGateway:
    """Returns a scripted sequence of replies, one per `chat` call."""

    def __init__(self, scripted_replies):
        self.default_model = "fake-model"
        self._replies = list(scripted_replies)
        self.calls = []

    def chat(self, messages, model=None, options=None, temperature=0.2):
        self.calls.append(messages)
        if not self._replies:
            raise AssertionError("FakeGateway ran out of scripted replies")
        return self._replies.pop(0)


def test_direct_final_answer_no_tool_call():
    gateway = FakeGateway(["FINAL_ANSWER: Paris is the capital of France."])
    agent = ReasoningAgent(gateway)
    task = Task(input_text="What is the capital of France?", agent_type="reasoning")

    response = agent.run(task)

    assert response.status == TaskStatus.SUCCESS
    assert response.content == "Paris is the capital of France."
    assert len(response.steps) == 1
    assert response.steps[0].tool_called is None


def test_uses_python_tool_then_final_answer():
    gateway = FakeGateway(
        [
            "```python\nprint(21 * 2)\n```",
            "FINAL_ANSWER: The result is 42.",
        ]
    )
    agent = ReasoningAgent(gateway)
    task = Task(input_text="What is 21 times 2?", agent_type="reasoning")

    response = agent.run(task)

    assert response.status == TaskStatus.SUCCESS
    assert response.content == "The result is 42."
    assert len(response.steps) == 2
    assert response.steps[0].tool_called == "python_tool"
    assert response.steps[0].tool_output == "42"


def test_exceeds_max_steps_fails_gracefully():
    # Always returns a code block, never a FINAL_ANSWER -> should stop
    # after max_steps rather than looping forever.
    gateway = FakeGateway(["```python\nprint(1)\n```"] * 10)
    agent = ReasoningAgent(gateway)
    task = Task(input_text="loop forever", agent_type="reasoning", max_steps=3)

    response = agent.run(task)

    assert response.status == TaskStatus.FAILED
    assert "max_steps" in response.error
    assert len(response.steps) == 3

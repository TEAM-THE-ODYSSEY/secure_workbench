from agentic_engine.agents.mathematical_agent import MathematicalAgent
from agentic_engine.schemas.task import Task, TaskStatus
from tests.test_reasoning_agents import FakeGateway


def test_mathematical_agent_verifies_via_sandbox():
    gateway = FakeGateway(
        [
            "```python\nimport sympy\nprint(sympy.factorial(5))\n```",
            "FINAL_ANSWER: 5! = 120",
        ]
    )
    agent = MathematicalAgent(gateway)
    task = Task(input_text="What is 5 factorial?", agent_type="mathematical")

    response = agent.run(task)

    assert response.status == TaskStatus.SUCCESS
    assert response.agent_name == "mathematical"
    assert "120" in response.content
    # Confirm the math-specific system prompt was actually used
    first_call_messages = gateway.calls[0]
    assert first_call_messages[0]["role"] == "system"
    assert "NEVER compute a numeric result yourself" in first_call_messages[0]["content"]

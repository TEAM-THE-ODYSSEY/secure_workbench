"""
MathematicalAgent
-------------------
Specialized for numerical/mathematical tasks. Unlike ReasoningAgent
(which uses code optionally), this agent is instructed to ALWAYS
compute via the Python sandbox rather than trust the model's own
arithmetic -- LLMs are unreliable at exact arithmetic, sandboxed Python
is not.

It reuses ReasoningAgent's think/act/observe loop verbatim (same
```python``` fenced-block protocol) but supplies a stricter,
math-specific system prompt via the constructor -- no global state,
no monkey-patching, so it's safe to run multiple agents concurrently.
"""

from __future__ import annotations

from typing import Optional

from .base_agent import BaseAgent
from .reasoning_agent import ReasoningAgent
from ..schemas.task import Task
from ..schemas.response import AgentResponse
from ..tools.python_tool import PythonTool

MATH_SYSTEM_PROMPT = """You are a precise mathematical reasoning agent running fully offline on a local model.

Rules:
- NEVER compute a numeric result yourself. For every arithmetic, algebraic,
  statistical, or numeric step, respond with ONLY a fenced Python code block:
```python
# use sympy for symbolic math if needed, otherwise plain Python
print(...)
```
  Nothing else in that turn.
- After you have the verified numeric result(s) from tool output, respond
  with your final answer prefixed exactly with "FINAL_ANSWER:" followed by
  a clear, complete answer (including units/interpretation if relevant).
- If the problem is symbolic, prefer using the `sympy` library inside the
  code block for exact results.
- Never claim to browse the internet or call external services.
"""


class MathematicalAgent(BaseAgent):
    name = "mathematical"

    def __init__(self, gateway, model: Optional[str] = None, python_tool: Optional[PythonTool] = None):
        super().__init__(gateway, model)
        self._engine = ReasoningAgent(
            gateway,
            model=model,
            python_tool=python_tool,
            system_prompt=MATH_SYSTEM_PROMPT,
        )

    def run(self, task: Task) -> AgentResponse:
        response = self._engine.run(task)
        response.agent_name = self.name
        return response

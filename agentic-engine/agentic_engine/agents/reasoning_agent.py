"""
ReasoningAgent
---------------
General-purpose conversational / multi-step reasoning agent.

Implements a small ReAct-style loop:
  1. Ask the model to either give a FINAL_ANSWER, or emit a fenced
     ```python``` block it wants executed.
  2. If it emitted code, run it in the sandbox via PythonTool, feed the
     result back as a new message, and loop.
  3. Stop at FINAL_ANSWER, or when `task.max_steps` is reached.

This is intentionally simple and dependency-free (no agent framework)
so it's easy to extend with more tools later — add a tool, add a
branch in `_maybe_extract_tool_call`, done.
"""

from __future__ import annotations

import re
from typing import Optional

from .base_agent import BaseAgent
from ..schemas.task import Task, TaskStatus
from ..schemas.response import AgentResponse, StepRecord
from ..tools.gateway import OllamaGatewayError
from ..tools.python_tool import PythonTool

_CODE_BLOCK_RE = re.compile(r"```python\s*(.*?)```", re.DOTALL | re.IGNORECASE)

SYSTEM_PROMPT = """You are a careful reasoning agent running fully offline on a local model.

Rules:
- If solving the task requires computation, data manipulation, or you are
  not fully certain of an arithmetic/logical result, respond with ONLY a
  single fenced Python code block, e.g.:
```python
print(2 ** 10)
```
  Nothing else in that turn — no explanation before or after the block.
- Once you have everything you need, respond with your final answer
  prefixed exactly with "FINAL_ANSWER:" on its own line, followed by the
  answer for the user.
- Keep intermediate reasoning brief. Never claim to browse the internet
  or call external services — you have no such access.
"""


class ReasoningAgent(BaseAgent):
    name = "reasoning"

    def __init__(
        self,
        gateway,
        model: Optional[str] = None,
        python_tool: Optional[PythonTool] = None,
        system_prompt: Optional[str] = None,
    ):
        super().__init__(gateway, model)
        self.python_tool = python_tool or PythonTool()
        self.system_prompt = system_prompt or SYSTEM_PROMPT

    def run(self, task: Task) -> AgentResponse:
        steps: list[StepRecord] = []
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": task.input_text},
        ]

        for step_index in range(task.max_steps):
            try:
                reply = self.gateway.chat(messages=messages, model=self.model)
            except OllamaGatewayError as exc:
                return AgentResponse(
                    task_id=task.id,
                    agent_name=self.name,
                    status=TaskStatus.FAILED,
                    content="",
                    steps=steps,
                    error=str(exc),
                )

            code = self._extract_code(reply)

            if code is None:
                final_text = self._strip_final_answer_prefix(reply)
                steps.append(StepRecord(step_index=step_index, thought=reply))
                return AgentResponse(
                    task_id=task.id,
                    agent_name=self.name,
                    status=TaskStatus.SUCCESS,
                    content=final_text,
                    steps=steps,
                )

            tool_result = self.python_tool.run(code)
            steps.append(
                StepRecord(
                    step_index=step_index,
                    thought=reply,
                    tool_called=self.python_tool.name,
                    tool_input=code,
                    tool_output=tool_result.output,
                    error=tool_result.error if not tool_result.success else None,
                )
            )

            messages.append({"role": "assistant", "content": reply})
            observation = (
                f"TOOL_RESULT (success={tool_result.success}):\n"
                f"stdout: {tool_result.output}\n"
                f"stderr/error: {tool_result.error}"
            )
            messages.append({"role": "user", "content": observation})

        # Ran out of steps without a FINAL_ANSWER
        return AgentResponse(
            task_id=task.id,
            agent_name=self.name,
            status=TaskStatus.FAILED,
            content="",
            steps=steps,
            error=f"Exceeded max_steps ({task.max_steps}) without reaching a final answer.",
        )

    @staticmethod
    def _extract_code(reply: str) -> Optional[str]:
        match = _CODE_BLOCK_RE.search(reply)
        return match.group(1).strip() if match else None

    @staticmethod
    def _strip_final_answer_prefix(reply: str) -> str:
        text = reply.strip()
        if text.upper().startswith("FINAL_ANSWER:"):
            return text[len("FINAL_ANSWER:") :].strip()
        return text

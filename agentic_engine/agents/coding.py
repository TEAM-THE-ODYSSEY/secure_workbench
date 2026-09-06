from __future__ import annotations

from .base import BaseAgent


class CodingAgent(BaseAgent):
    def run(self, user_text, context, model, metadata):
        prompt = f"""
You are the coding agent.
The orchestrator will execute your Python code in a restricted sandbox.
When the request asks for code, return runnable Python in exactly one code block.
Do not put explanations before or after the code block.
When debugging existing code, preserve the user's intent and fix the actual defect.
Never claim execution unless the sandbox result supplied later proves it.
Do not use network, subprocess, shell commands, or unsafe OS operations.

USER REQUEST:
{user_text}

CONTEXT:
{context or '[none]'}
""".strip()
        return self.llm.generate(model, prompt)

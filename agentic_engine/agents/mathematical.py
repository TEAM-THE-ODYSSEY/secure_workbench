from __future__ import annotations

from .base import BaseAgent


class MathematicalAgent(BaseAgent):
    def run(self, user_text, context, model, metadata):
        prompt = f"""
You are the mathematical agent.
Solve the user's mathematical task carefully.
Show steps when requested. State formulas, substitutions and final result.
Do not invent missing values. Check arithmetic before answering.
Return a clear human-readable mathematical explanation.

USER REQUEST:
{user_text}

CONTEXT:
{context or '[none]'}
""".strip()
        return self.llm.generate(model, prompt)

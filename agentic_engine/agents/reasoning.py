from __future__ import annotations

from typing import Any, Dict, List, Set
from .base import BaseAgent
from ..models.capabilities import TaskCapability


class ReasoningAgent(BaseAgent):
    name = "reasoning"
    task_types = ["reasoning"]
    capabilities: Set[str] = {
        TaskCapability.REASONING.value,
        TaskCapability.RETRIEVAL.value,
        TaskCapability.STRUCTURED_OUTPUT.value,
    }
    input_types = ["text"]
    output_types = ["text", "json"]
    required_tools = []
    validator_chain = ["text"]

    def run(
        self,
        user_text: str,
        context: str = "",
        model: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        metadata = metadata or {}
        history = metadata.get("history", [])
        recent_history = history[-10:]

        history_text = "\n".join(
            f"{item.get('role', 'unknown').upper()}: {item.get('content', '')}"
            for item in recent_history
        )

        prompt = f"""You are a helpful AI reasoning assistant.
Answer the CURRENT USER QUESTION directly, analytically, and with zero hallucination.

IMPORTANT RULES:
- Answer only the current question.
- Do not invent information or continuous conversation.
- Use conversation history only to understand context.
- Ground answer in the provided file and company context.

CONVERSATION HISTORY:
{history_text if history_text else "No previous conversation."}

CURRENT USER QUESTION:
{user_text}

CONTEXT:
{context if context else "No additional context."}

YOUR ANSWER:
"""
        return self.llm.generate(prompt=prompt, model=model)
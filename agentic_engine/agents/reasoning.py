from typing import Any

from .base import BaseAgent


class ReasoningAgent(BaseAgent):

    def run(
        self,
        user_text: str,
        context: str = "",
        model: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> str:

        metadata = metadata or {}
        history = metadata.get("history", [])

        # Keep only recent conversation turns.
        recent_history = history[-10:]

        history_text = "\n".join(
            f"{item.get('role', 'unknown').upper()}: "
            f"{item.get('content', '')}"
            for item in recent_history
        )

        prompt = f"""
You are a helpful AI assistant.

Answer the CURRENT USER QUESTION directly.

IMPORTANT RULES:
- Do NOT continue or invent a conversation.
- Do NOT generate fake USER/ASSISTANT dialogue.
- Do NOT repeat the entire conversation.
- Do NOT create multiple imaginary AI responses.
- Use conversation history only to understand context.
- If the answer exists in the conversation history, use it.
- Answer only the current question.
- For a simple question, give a short direct answer.
- Do not mention files unless a file is actually provided.
- Do not invent information.

CONVERSATION HISTORY:
{history_text if history_text else "No previous conversation."}

CURRENT USER QUESTION:
{user_text}

FILE CONTEXT:
{context if context else "No file context."}

YOUR ANSWER:
"""

        result = self.llm.generate(
            prompt=prompt,
            model=model,
        )

        if result is None:
            return "I could not generate an answer."

        return str(result).strip()
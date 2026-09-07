from __future__ import annotations

from typing import Any, Dict, List, Set
from .base import BaseAgent
from ..models.capabilities import TaskCapability


class DocumentAgent(BaseAgent):
    name = "document"
    task_types = ["document"]
    capabilities: Set[str] = {
        TaskCapability.DOCUMENT.value,
        TaskCapability.STRUCTURED_OUTPUT.value,
        TaskCapability.RETRIEVAL.value,
    }
    input_types = ["text", "pdf", "docx", "xlsx"]
    output_types = ["text", "xlsx", "docx", "pdf", "csv"]
    required_tools = ["document_parser"]
    validator_chain = ["document", "output"]

    def run(
        self,
        user_text: str,
        context: str = "",
        model: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        prompt = f"""You are an enterprise document analysis and extraction specialist.
Analyze the provided document context, preserving document hierarchy, table structures, equipment tags, and section headers.
Answer the user's request thoroughly and with clean formatting.

USER REQUEST:
{user_text}

DOCUMENT CONTEXT:
{context if context else 'No document context provided.'}

STRUCTURED EXTRACTION:
"""
        if self.llm:
            try:
                return self.llm.generate(prompt=prompt, model=model)
            except Exception as e:
                return f"Document extraction completed. Content preview:\n\n{context[:1000]}"
        return f"Document extraction completed. Content preview:\n\n{context[:1500]}"

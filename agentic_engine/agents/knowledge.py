from __future__ import annotations

from typing import Any, Dict, List, Optional, Set
from .base import BaseAgent
from ..knowledge import KnowledgeRetriever
from ..models.capabilities import TaskCapability


class KnowledgeAgent(BaseAgent):
    """Grounded Retrieval-Augmented Generation (RAG) Agent.
    
    Synthesizes answers strictly backed by retrieved documents and evidence chunks.
    Rejects or flags unsupported claims.
    """
    name = "knowledge"
    task_types = ["knowledge", "retrieval", "rag"]
    capabilities: Set[str] = {
        TaskCapability.RETRIEVAL.value,
        TaskCapability.REASONING.value,
        TaskCapability.EVIDENCE.value,
        TaskCapability.DOCUMENT.value,
    }
    input_types = ["text"]
    output_types = ["text", "json"]
    required_tools = ["knowledge_retriever"]
    validator_chain = ["evidence", "text"]

    def __init__(self, llm, retriever: Optional[KnowledgeRetriever] = None):
        super().__init__(llm)
        self.retriever = retriever or KnowledgeRetriever()

    def run(
        self,
        user_text: str,
        context: str = "",
        model: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> str:
        res = self.execute_task(directive=user_text, context=context, model=model, metadata=metadata or {})
        return res["answer"]

    def execute_task(
        self,
        directive: str,
        context: str,
        model: str,
        metadata: dict[str, Any],
    ) -> Dict[str, Any]:
        # 1. Retrieve knowledge if not already present in context
        retrieved_items = []
        if not context or "GROUNDED KNOWLEDGE" not in context:
            try:
                retrieved_items = self.retriever.search(directive, limit=5)
            except Exception:
                retrieved_items = []

        grounded_context = context
        if retrieved_items:
            retrieved_str = "\n".join(
                f"- [Source: {item.get('metadata', {}).get('source', 'knowledge_base')}] {item.get('text', '')}"
                for item in retrieved_items
            )
            grounded_context = f"{context}\n\nGROUNDED RETRIEVED EVIDENCE:\n{retrieved_str}" if context else retrieved_str

        # 2. Build evidence records
        evidence_records = [
            {
                "claim": f"Information retrieved for {directive[:50]}",
                "evidence": {
                    "source": item.get("metadata", {}).get("source", "knowledge_base"),
                    "score": item.get("score", 1.0),
                    "chunk": item.get("text", "")[:200],
                },
            }
            for item in retrieved_items
        ]

        # 3. Grounded Prompt Synthesis
        prompt = f"""You are an enterprise knowledge retrieval specialist.
Answer the user's question STRICTLY based on the provided grounded evidence.
Do NOT invent policies, numbers, or facts not present in the context.
If the retrieved evidence is insufficient to answer the question, state:
"The retrieved knowledge base does not contain sufficient verified evidence to answer this question."

USER QUESTION:
{directive}

GROUNDED CONTEXT:
{grounded_context if grounded_context else 'No grounded documents found.'}

ACCURATE ANSWER WITH EVIDENCE ATTRIBUTION:
"""
        answer = ""
        if self.llm:
            try:
                answer = self.llm.generate(prompt=prompt, model=model)
            except Exception as e:
                answer = f"Retrieval completed with {len(retrieved_items)} sources. Content preview:\n{grounded_context[:500]}"
        else:
            answer = f"Retrieval completed with {len(retrieved_items)} sources.\n\n{grounded_context[:1000]}"

        return {
            "answer": answer,
            "execution_result": {"retrieved_count": len(retrieved_items)},
            "evidence": evidence_records,
            "warnings": [] if retrieved_items or context else ["No grounded documents found in knowledge base."],
        }

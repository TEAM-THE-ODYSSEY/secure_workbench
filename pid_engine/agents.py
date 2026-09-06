from __future__ import annotations
import json
from typing import Any

class PIDReasoningAgent:
    """Graph-first reasoning helper. LLM integration can be added through OllamaGateway."""
    def __init__(self, gateway=None, model: str | None = None):
        self.gateway = gateway
        self.model = model

    def answer(self, question: str, analysis: Any, evidence: list[str] | None = None) -> str:
        graph = analysis.graph if hasattr(analysis, "graph") else analysis
        evidence = evidence or []
        prompt = f"""You are a P&ID reasoning agent.
Answer only from the supplied structured P&ID and evidence.
Do not invent engineering facts. If evidence is insufficient, say that human
verification is required.

QUESTION:
{question}

STRUCTURED P&ID:
{json.dumps(graph, indent=2)}

EVIDENCE:
{json.dumps(evidence, indent=2)}
"""
        if self.gateway is None:
            return "LLM gateway not configured. Structured graph is available for deterministic querying."
        return self.gateway.chat([
            {"role": "system", "content": "You are an evidence-grounded P&ID reasoning agent."},
            {"role": "user", "content": prompt},
        ], model=self.model)

class PIDValidator:
    def __init__(self, threshold: float = 0.75):
        self.threshold = threshold

    def validate(self, analysis) -> dict:
        obj_scores = [o.association_confidence for o in analysis.objects]
        rel_scores = [r.confidence for r in analysis.relationships]
        scores = obj_scores + rel_scores
        confidence = sum(scores)/len(scores) if scores else 0.0
        return {
            "confidence": round(confidence, 4),
            "decision": "output" if confidence >= self.threshold else "human_verification",
            "warnings": analysis.warnings,
        }

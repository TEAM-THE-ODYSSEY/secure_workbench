from __future__ import annotations

import json
import re
from typing import Any

from ..llm import OllamaClient
from ..state.schema import ExecutionPlanState
from .complexity import ComplexityAnalyzer


class Planner:
    """LLM-assisted planner. It decides the task; it is not a keyword router.

    The JSON contract is intentionally small so a local open-weight model can
    produce it reliably. If planning fails, a conservative non-LLM fallback is
    used only to keep the engine operational.
    """

    SYSTEM_PROMPT = """
You are the planning brain of a local Agentic AI Workbench.
You do NOT solve the user's task. You decide how the system should solve it.
Return ONLY valid JSON. No markdown and no explanation outside JSON.

Allowed task_type: reasoning, mathematical, coding.
Allowed complexity: small, medium, large.
Allowed agent: reasoning, mathematical, coding.
Allowed output_type: text, json, csv, xlsx, docx, pdf.
Allowed validation_type: text, json, math, code.
Allowed tools: python_sandbox, knowledge_retriever.

Decide from the user's actual intent, not from isolated keywords.
Use a small task when one straightforward operation is enough.
Use medium when multiple reasoning steps are needed.
Use large for substantial documents, multi-step coding, comparison, design,
large context, or tasks requiring iterative verification.

Return exactly this shape:
{
  "task_type": "reasoning|mathematical|coding",
  "task_reason": "short reason",
  "complexity": "small|medium|large",
  "agent": "reasoning|mathematical|coding",
  "retrieval": true,
  "tools": [],
  "output_type": "text|json|csv|xlsx|docx|pdf",
  "validation_type": "text|json|math|code",
  "max_iterations": 1
}
""".strip()

    def __init__(self, llm: OllamaClient | None = None):
        self.llm = llm
        self.complexity = ComplexityAnalyzer()

    @staticmethod
    def _output_type(text: str) -> str:
        t = (text or "").lower()
        if re.search(r"\b(json)\b", t):
            return "json"
        if re.search(r"\b(csv)\b", t):
            return "csv"
        if re.search(r"\b(excel|xlsx)\b", t):
            return "xlsx"
        if re.search(r"\b(word|docx)\b", t):
            return "docx"
        if re.search(r"\b(pdf)\b", t):
            return "pdf"
        return "text"

    @staticmethod
    def _clean_json(raw: str) -> dict[str, Any]:
        raw = raw.strip()
        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.I | re.S)
        if fenced:
            raw = fenced.group(1)
        start, end = raw.find("{"), raw.rfind("}")
        if start >= 0 and end > start:
            raw = raw[start:end + 1]
        return json.loads(raw)

    def _fallback(self, text: str, context_chars: int, has_file: bool) -> ExecutionPlanState:
        """Small conservative fallback; no large keyword table."""
        t = (text or "").lower()
        output = self._output_type(text)
        complexity = self.complexity.analyze(text, context_chars)

        # Intent-level signals only; this is a safety fallback, not the brain.
        coding = any(x in t for x in (
            "write code", "write a program", "debug", "implement", "python code",
            "java code", "javascript code", "fix this code", "create a function",
            "create a class", "stack trace", "sql query",
        ))
        math = bool(re.search(r"(?<!\w)(\d+(?:\.\d+)?\s*[+\-*/^=]\s*\d)", t)) or any(
            x in t for x in ("solve equation", "calculate", "derivative", "integral", "probability", "matrix")
        )

        if coding and not math:
            task, agent, validation = "coding", "coding", "code"
            tools = ["python_sandbox"]
        elif math and not coding:
            task, agent, validation = "mathematical", "mathematical", "math"
            tools = []
        else:
            task, agent, validation = "reasoning", "reasoning", "text"
            tools = []

        retrieval = any(x in t for x in ("our company", "internal policy", "company document", "knowledge base"))
        if has_file and context_chars > 0:
            retrieval = retrieval or False

        iterations = 3 if complexity == "large" or task == "coding" else 1
        return ExecutionPlanState(task, "Conservative fallback plan", complexity, agent,
                                  retrieval, tools, output, validation, iterations)

    def plan(self, text: str, context_chars: int = 0, has_file: bool = False) -> ExecutionPlanState:
        if self.llm is None:
            return self._fallback(text, context_chars, has_file)

        prompt = (
            self.SYSTEM_PROMPT
            + "\n\nUSER REQUEST:\n"
            + (text or "[file supplied without a question]")
            + f"\n\nCONTEXT CHARACTERS: {context_chars}"
            + f"\nFILE SUPPLIED: {has_file}"
        )
        try:
            raw = self.llm.generate(
                model=self._planner_model(),
                prompt=prompt,
                parameters={"temperature": 0.0, "num_predict": 700},
            )
            data = self._clean_json(raw)
            return self._normalize(data, text, context_chars, has_file)
        except Exception:
            return self._fallback(text, context_chars, has_file)

    def _planner_model(self) -> str:
        # Planning needs to be local and cheap. The engine may override this
        # through AGENT_PLANNER_MODEL in a future configuration.
        import os
        return os.getenv("AGENT_PLANNER_MODEL", "tinyllama:latest")

    def _normalize(self, data: dict[str, Any], text: str, context_chars: int, has_file: bool) -> ExecutionPlanState:
        allowed_tasks = {"reasoning", "mathematical", "coding"}
        allowed_complexity = {"small", "medium", "large"}
        allowed_output = {"text", "json", "csv", "xlsx", "docx", "pdf"}
        allowed_validation = {"text", "json", "math", "code"}
        allowed_tools = {"python_sandbox", "knowledge_retriever"}

        task = str(data.get("task_type", "reasoning")).lower()
        agent = str(data.get("agent", task)).lower()
        complexity = str(data.get("complexity", "medium")).lower()
        output = str(data.get("output_type", self._output_type(text))).lower()
        validation = str(data.get("validation_type", "text")).lower()

        if task not in allowed_tasks:
            raise ValueError("Invalid task_type from planner")
        if agent not in allowed_tasks:
            agent = task
        if complexity not in allowed_complexity:
            complexity = self.complexity.analyze(text, context_chars)
        if output not in allowed_output:
            output = self._output_type(text)

        # Validator is tied to the actual task unless a structured-output
        # validator was explicitly requested.
        if output == "json":
            validation = "json"
        elif task == "coding":
            validation = "code"
        elif task == "mathematical":
            validation = "math"
        else:
            validation = "text"
        if validation not in allowed_validation:
            validation = "text"

        tools = [x for x in data.get("tools", []) if x in allowed_tools]
        if task == "coding" and "python_sandbox" not in tools:
            tools.append("python_sandbox")

        retrieval = bool(data.get("retrieval", False))
        iterations = int(data.get("max_iterations", 1) or 1)
        iterations = max(1, min(iterations, 3))
        if complexity == "large" or task == "coding":
            iterations = max(iterations, 3)

        return ExecutionPlanState(
            task_type=task,
            task_reason=str(data.get("task_reason", ""))[:500],
            complexity=complexity,
            agent=agent,
            retrieval=retrieval,
            tools=tools,
            output_type=output,
            validation_type=validation,
            max_iterations=iterations,
        )

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

Allowed task_type: reasoning, mathematical, coding, document, multimodal, pid.
Allowed complexity: small, medium, large.
Allowed domain: general, industrial, technical, finance, legal.
Allowed agent: reasoning, mathematical, coding, multimodal.
Allowed output_type: text, json, csv, xlsx, docx, pdf.
Allowed validation_type: text, json, math, code, document, evidence.
Allowed tools: python_sandbox, knowledge_retriever, document_parser, ocr, pid_engine.

Decide from the user's actual intent, not from isolated keywords:
- reasoning: understanding, comparison, explanation, analysis, decision support.
- mathematical: equations, algebra, statistics, numerical verification.
- coding: scripts, data transformation, program generation, execution in Docker.
- document: analyzing structured reports, PDFs, DOCX, XLSX, preserving tables/metadata.
- multimodal: visual diagrams, scanned charts, OCR extraction.
- pid: Piping & Instrumentation Diagrams, detecting equipment (valves, pumps, vessels), process lines, and topology.

Return exactly this shape:
{
  "task_type": "reasoning|mathematical|coding|document|multimodal|pid",
  "task_reason": "short reason",
  "complexity": "small|medium|large",
  "domain": "general|industrial|technical",
  "agent": "reasoning|mathematical|coding|multimodal",
  "retrieval": true,
  "tools": [],
  "output_type": "text|json|csv|xlsx|docx|pdf",
  "validation_type": "text|json|math|code|document|evidence",
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

    def _fallback(self, text: str, context_chars: int, has_file: bool, file_path: str | None = None) -> ExecutionPlanState:
        """Conservative intent-driven fallback for the execution coordinator."""
        from pathlib import Path
        t = (text or "").lower()
        output = self._output_type(text)
        complexity = self.complexity.analyze(text, context_chars)
        ext = Path(file_path).suffix.lower() if file_path else ""

        # Check for P&ID engineering schematic
        is_pid_intent = bool(re.search(r"\b(p&id|pid|piping and instrumentation|process line|valve|pump|vessel|tank|compressor)\b", t))
        is_image_file = ext in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}

        if is_image_file and (is_pid_intent or "pid" in (file_path or "").lower()):
            task, agent, validation = "pid", "multimodal", "evidence"
            domain = "industrial"
            tools = ["pid_engine", "ocr"]
            complexity = "large"
        elif is_image_file:
            task, agent, validation = "multimodal", "multimodal", "document"
            domain = "general"
            tools = ["ocr"]
        elif ext in {".pdf", ".docx", ".xlsx", ".pptx"} or (has_file and context_chars > 0 and not is_pid_intent):
            task, agent, validation = "document", "multimodal", "document"
            domain = "industrial" if any(x in t for x in ("mrpl", "refinery", "plant", "shutdown", "equipment")) else "general"
            tools = ["document_parser"]
            complexity = "large" if context_chars > 3000 else "medium"
        else:
            coding = bool(re.search(
                r"\b(code|coding|program|script|function|class|debug|implement|python|java|javascript|c\+\+|sql|query|algorithm)\b",
                t,
            ))
            math = bool(re.search(r"(?<!\w)(\d+(?:\.\d+)?\s*[+\-*/^=]\s*\d)", t)) or any(
                x in t for x in ("solve equation", "calculate", "derivative", "integral", "probability", "matrix", "algebra")
            )

            if coding:
                task, agent, validation = "coding", "coding", "code"
                domain = "general"
                tools = ["python_sandbox"]
            elif math:
                task, agent, validation = "mathematical", "mathematical", "math"
                domain = "general"
                tools = []
            elif is_pid_intent:
                task, agent, validation = "pid", "multimodal", "evidence"
                domain = "industrial"
                tools = ["pid_engine", "ocr"]
                complexity = "large"
            else:
                task, agent, validation = "reasoning", "reasoning", "text"
                domain = "general"
                tools = []

        retrieval = any(x in t for x in ("our company", "internal policy", "company document", "knowledge base", "procedure", "shutdown", "mrpl"))
        if task == "reasoning" and retrieval:
            tools.append("knowledge_retriever")

        iterations = 3 if complexity == "large" or task == "coding" else 1
        return ExecutionPlanState(
            task_type=task,
            task_reason="Intent-driven coordination plan",
            complexity=complexity,
            domain=domain,
            agent=agent,
            retrieval=retrieval,
            tools=tools,
            output_type=output,
            validation_type=validation,
            max_iterations=iterations,
        )

    def plan(self, text: str, context_chars: int = 0, has_file: bool = False, file_path: str | None = None) -> ExecutionPlanState:
        if self.llm is None:
            return self._fallback(text, context_chars, has_file, file_path)

        prompt = (
            self.SYSTEM_PROMPT
            + "\n\nUSER REQUEST:\n"
            + (text or "[file supplied without a question]")
            + f"\n\nCONTEXT CHARACTERS: {context_chars}"
            + f"\nFILE SUPPLIED: {has_file}"
            + f"\nFILE PATH: {file_path or 'none'}"
        )
        try:
            raw = self.llm.generate(
                model=self._planner_model(),
                prompt=prompt,
                parameters={"temperature": 0.0, "num_predict": 700},
            )
            data = self._clean_json(raw)
            return self._normalize(data, text, context_chars, has_file, file_path)
        except Exception:
            return self._fallback(text, context_chars, has_file, file_path)

    def _planner_model(self) -> str:
        import os
        return os.getenv("AGENT_PLANNER_MODEL", "tinyllama:latest")

    def _normalize(self, data: dict[str, Any], text: str, context_chars: int, has_file: bool, file_path: str | None = None) -> ExecutionPlanState:
        allowed_tasks = {"reasoning", "mathematical", "coding", "document", "multimodal", "pid"}
        allowed_complexity = {"small", "medium", "large"}
        allowed_agents = {"reasoning", "mathematical", "coding", "multimodal"}
        allowed_output = {"text", "json", "csv", "xlsx", "docx", "pdf"}
        allowed_validation = {"text", "json", "math", "code", "document", "evidence"}
        allowed_tools = {"python_sandbox", "knowledge_retriever", "document_parser", "ocr", "pid_engine"}

        task = str(data.get("task_type", "reasoning")).lower()
        agent = str(data.get("agent", "reasoning")).lower()
        complexity = str(data.get("complexity", "medium")).lower()
        domain = str(data.get("domain", "general")).lower()
        output = str(data.get("output_type", self._output_type(text))).lower()
        validation = str(data.get("validation_type", "text")).lower()

        if task not in allowed_tasks:
            raise ValueError(f"Invalid task_type from planner: {task}")
        if agent not in allowed_agents:
            agent = "multimodal" if task in {"document", "multimodal", "pid"} else task
        if complexity not in allowed_complexity:
            complexity = self.complexity.analyze(text, context_chars)
        if output not in allowed_output:
            output = self._output_type(text)

        # Map validation strategy to task & output
        if task == "pid":
            validation = "evidence"
        elif task in {"document", "multimodal"}:
            validation = "document" if output != "json" else "json"
        elif task == "coding":
            validation = "code"
        elif task == "mathematical":
            validation = "math"
        elif output == "json":
            validation = "json"
        else:
            validation = "text"

        if validation not in allowed_validation:
            validation = "text"

        tools = [x for x in data.get("tools", []) if x in allowed_tools]
        if task == "coding" and "python_sandbox" not in tools:
            tools.append("python_sandbox")
        if task == "pid" and "pid_engine" not in tools:
            tools.append("pid_engine")
        if task in {"pid", "multimodal"} and "ocr" not in tools:
            tools.append("ocr")
        if task == "document" and "document_parser" not in tools:
            tools.append("document_parser")

        retrieval = bool(data.get("retrieval", False))
        iterations = int(data.get("max_iterations", 1) or 1)
        iterations = max(1, min(iterations, 3))
        if complexity == "large" or task in {"coding", "pid"}:
            iterations = max(iterations, 3)

        return ExecutionPlanState(
            task_type=task,
            task_reason=str(data.get("task_reason", ""))[:500],
            complexity=complexity,
            domain=domain,
            agent=agent,
            retrieval=retrieval,
            tools=tools,
            output_type=output,
            validation_type=validation,
            max_iterations=iterations,
        )

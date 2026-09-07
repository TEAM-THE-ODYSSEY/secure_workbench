from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .complexity import MultiDimensionalComplexityAnalyzer
from .execution_plan import DAGNodeDefinition, ExecutionPlan
from .policy import PolicyEngine
from .router import CapabilityRouter
from ..llm import OllamaClient


class ExecutionPlanner:
    """Canonical Capability-Driven Execution Planner.
    
    Translates normalized user requests and inputs into formal, inspectable,
    and budgeted ExecutionPlans.
    """

    SYSTEM_PROMPT = """
You are the planning brain of a local Agentic AI Workbench.
You do NOT solve the user's task. You decide how the system should solve it.
Return ONLY valid JSON. No markdown and no explanation outside JSON.

Allowed task_type: reasoning, mathematical, coding, document, multimodal, pid.
Allowed complexity: small, medium, large.
Allowed domain: general, industrial, technical, finance, legal.
Allowed agent: reasoning, mathematical, coding, document, multimodal, pid.
Allowed output_type: text, json, csv, xlsx, docx, pdf.
Allowed validator_chain: ["text"], ["code"], ["math"], ["document"], ["evidence", "topology", "output"].
Allowed tools: python_sandbox, knowledge_retriever, document_parser, ocr, pid_engine.

Return exactly this shape:
{
  "task_type": "reasoning|mathematical|coding|document|multimodal|pid",
  "task_reason": "short reason",
  "complexity": "small|medium|large",
  "domain": "general|industrial|technical",
  "agent": "reasoning|mathematical|coding|document|multimodal|pid",
  "capabilities": ["reasoning", ...],
  "retrieval": true|false,
  "tools": [],
  "validator_chain": ["text"],
  "output_type": "text|json|csv|xlsx|docx|pdf",
  "max_iterations": 1,
  "max_tool_calls": 4
}
""".strip()

    def __init__(self, llm: Optional[OllamaClient] = None):
        self.llm = llm
        self.complexity_analyzer = MultiDimensionalComplexityAnalyzer()
        self.router = CapabilityRouter()
        self.policy = PolicyEngine()

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

    def _clean_json(self, raw: str) -> Dict[str, Any]:
        raw = raw.strip()
        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.I | re.S)
        if fenced:
            raw = fenced.group(1)
        start, end = raw.find("{"), raw.rfind("}")
        if start >= 0 and end > start:
            raw = raw[start:end + 1]
        return json.loads(raw)

    def plan(
        self,
        text: str,
        context_chars: int = 0,
        has_file: bool = False,
        file_path: str | None = None,
    ) -> ExecutionPlan:
        plan_id = f"plan_{uuid.uuid4().hex[:8]}"

        if self.llm is None:
            return self._build_deterministic_plan(plan_id, text, context_chars, has_file, file_path)

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
            return self._normalize_and_enrich(plan_id, data, text, context_chars, has_file, file_path)
        except Exception:
            return self._build_deterministic_plan(plan_id, text, context_chars, has_file, file_path)

    @staticmethod
    def _planner_model() -> str:
        import os
        return os.getenv("AGENT_PLANNER_MODEL", "tinyllama:latest")

    def _build_deterministic_plan(
        self,
        plan_id: str,
        text: str,
        context_chars: int,
        has_file: bool,
        file_path: str | None = None,
    ) -> ExecutionPlan:
        t = (text or "").lower()
        output_fmt = self._output_type(text)
        ext = Path(file_path).suffix.lower() if file_path else ""

        # Intent classification
        is_pid_intent = bool(re.search(r"\b(p&id|pid|piping and instrumentation|process line|valve|pump|vessel|tank|compressor)\b", t))
        is_image = ext in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}

        if is_image and (is_pid_intent or "pid" in (file_path or "").lower()):
            task_type = "pid"
            agent = "pid"
            domain = "industrial"
            tools = ["ocr", "pid_engine"]
            validator_chain = ["evidence", "topology", "output"]
            model_policy = "pid_multimodal"
        elif is_image:
            task_type = "multimodal"
            agent = "multimodal"
            domain = "general"
            tools = ["ocr"]
            validator_chain = ["document", "output"]
            model_policy = "vision"
        elif ext in {".pdf", ".docx", ".xlsx", ".pptx"} or (has_file and context_chars > 0 and not is_pid_intent):
            task_type = "document"
            agent = "document"
            domain = "industrial" if any(x in t for x in ("mrpl", "refinery", "plant", "shutdown", "equipment")) else "general"
            tools = ["document_parser"]
            validator_chain = ["document", "output"]
            model_policy = "document_reasoning"
        else:
            coding = bool(re.search(
                r"\b(code|coding|program|script|function|class|debug|implement|python|java|javascript|c\+\+|sql|query|algorithm)\b",
                t,
            ))
            math = bool(re.search(r"(?<!\w)(\d+(?:\.\d+)?\s*[+\-*/^=]\s*\d)", t)) or any(
                x in t for x in ("solve equation", "calculate", "derivative", "integral", "probability", "matrix", "algebra")
            )

            if coding:
                task_type = "coding"
                agent = "coding"
                domain = "general"
                tools = ["python_sandbox"]
                validator_chain = ["code", "syntax", "output"]
                model_policy = "code_generation"
            elif math:
                task_type = "mathematical"
                agent = "mathematical"
                domain = "general"
                tools = []
                validator_chain = ["math", "output"]
                model_policy = "math_reasoning"
            elif is_pid_intent:
                task_type = "pid"
                agent = "pid"
                domain = "industrial"
                tools = ["ocr", "pid_engine"]
                validator_chain = ["evidence", "topology", "output"]
                model_policy = "pid_multimodal"
            else:
                task_type = "reasoning"
                agent = "reasoning"
                domain = "general"
                tools = []
                validator_chain = ["text"]
                model_policy = "analytical_reasoning"

        # Check knowledge retrieval
        retrieval = any(x in t for x in ("our company", "internal policy", "company document", "knowledge base", "procedure", "shutdown", "mrpl"))
        if retrieval and "knowledge_retriever" not in tools:
            tools.append("knowledge_retriever")

        # Multi-dimensional complexity evaluation
        comp_metrics = self.complexity_analyzer.analyze(
            text=text,
            context_chars=context_chars,
            has_file=has_file,
            file_path=file_path,
            task_type=task_type,
        )

        # Build DAG Nodes for multi-step tasks
        dag_nodes = self._generate_dag(task_type, tools, validator_chain, file_path)

        # Filter tools through policy allowlist
        tools = self.policy.filter_allowed_tools(agent, tools)

        # Budget calculation
        max_iters = 3 if comp_metrics.overall == "large" or task_type in {"coding", "pid"} else 1
        max_tools = 8 if comp_metrics.overall == "large" else 4
        timeout = 120.0 if comp_metrics.overall == "large" else 60.0

        required_caps = list(self.router.resolve_required_capabilities(
            task_type=task_type,
            retrieval_requested=retrieval,
            wants_structured_output=(output_fmt != "text"),
        ))

        return ExecutionPlan(
            plan_id=plan_id,
            task_type=task_type,
            complexity=comp_metrics.overall,
            capabilities=required_caps,
            domain=domain,
            agent=agent,
            model_policy=model_policy,
            tools=tools,
            validator_chain=validator_chain,
            validation_type=validator_chain[0] if validator_chain else "text",
            output_type=output_fmt,
            retrieval=retrieval,
            context_policy="task_scoped",
            max_iterations=max_iters,
            max_retries=2,
            max_tool_calls=max_tools,
            timeout_seconds=timeout,
            priority=1,
            dag_nodes=dag_nodes,
            task_reason=f"Deterministic capability-resolved plan for {task_type}",
        )

    def _normalize_and_enrich(
        self,
        plan_id: str,
        data: Dict[str, Any],
        text: str,
        context_chars: int,
        has_file: bool,
        file_path: str | None = None,
    ) -> ExecutionPlan:
        # Fall back gracefully to deterministic plan if JSON from small local LLM is malformed
        det = self._build_deterministic_plan(plan_id, text, context_chars, has_file, file_path)

        task_type = str(data.get("task_type", det.task_type)).lower()
        if task_type not in {"reasoning", "mathematical", "coding", "document", "multimodal", "pid"}:
            task_type = det.task_type
        # If deterministic rules resolved specialized domain (math/coding/pid), do not let LLM downgrade to generic reasoning
        if det.task_type in {"mathematical", "coding", "pid"} and task_type == "reasoning":
            task_type = det.task_type

        agent = str(data.get("agent", det.agent)).lower()
        allowed, _ = self.policy.validate_agent(agent)
        if not allowed or (det.task_type in {"mathematical", "coding", "pid"} and agent == "reasoning"):
            agent = det.agent

        output_type = str(data.get("output_type", det.output_type)).lower()
        allowed_out, _ = self.policy.validate_output_type(output_type)
        if not allowed_out:
            output_type = det.output_type

        tools = list(data.get("tools", det.tools))
        tools = self.policy.filter_allowed_tools(agent, tools)

        if det.task_type in {"mathematical", "coding", "pid"}:
            validator_chain = det.validator_chain
        else:
            validator_chain = data.get("validator_chain") or det.validator_chain
            if isinstance(validator_chain, str):
                validator_chain = [validator_chain]

        return ExecutionPlan(
            plan_id=plan_id,
            task_type=task_type,
            complexity=det.complexity,
            capabilities=det.capabilities,
            domain=str(data.get("domain", det.domain)),
            agent=agent,
            model_policy=det.model_policy,
            tools=tools,
            validator_chain=validator_chain,
            output_type=output_type,
            context_policy="task_scoped",
            max_iterations=det.max_iterations,
            max_retries=det.max_retries,
            max_tool_calls=det.max_tool_calls,
            timeout_seconds=det.timeout_seconds,
            priority=1,
            dag_nodes=det.dag_nodes,
            task_reason=str(data.get("task_reason", det.task_reason)),
        )

    @staticmethod
    def _generate_dag(
        task_type: str,
        tools: List[str],
        validator_chain: List[str],
        file_path: Optional[str] = None,
    ) -> List[DAGNodeDefinition]:
        """Builds explicit dependency DAG for multi-step tasks (Section 19)."""
        nodes = []
        if task_type == "pid":
            # Concurrent Trio Detection: OCR, Symbol Detection, Line Detection
            nodes.append(DAGNodeDefinition(
                node_id="node_ocr",
                node_type="tool",
                target="ocr",
                dependencies=[],
                parameters={"file_path": file_path},
            ))
            nodes.append(DAGNodeDefinition(
                node_id="node_symbols",
                node_type="tool",
                target="symbol_detector",
                dependencies=[],
                parameters={"file_path": file_path},
            ))
            nodes.append(DAGNodeDefinition(
                node_id="node_lines",
                node_type="tool",
                target="line_detector",
                dependencies=[],
                parameters={"file_path": file_path},
            ))
            # Spatial Fusion depends on Trio
            nodes.append(DAGNodeDefinition(
                node_id="node_fusion",
                node_type="tool",
                target="spatial_fusion",
                dependencies=["node_ocr", "node_symbols"],
            ))
            # Topology Builder depends on Fusion + Lines
            nodes.append(DAGNodeDefinition(
                node_id="node_topology",
                node_type="tool",
                target="topology_builder",
                dependencies=["node_fusion", "node_lines"],
            ))
            # Evidence & Synthesis
            nodes.append(DAGNodeDefinition(
                node_id="node_synthesis",
                node_type="agent",
                target="pid",
                dependencies=["node_topology"],
            ))
            # Validation
            nodes.append(DAGNodeDefinition(
                node_id="node_validation",
                node_type="validation",
                target="evidence_validator",
                dependencies=["node_synthesis"],
            ))
        elif task_type == "coding":
            nodes.append(DAGNodeDefinition(
                node_id="node_codegen",
                node_type="agent",
                target="coding",
                dependencies=[],
            ))
            nodes.append(DAGNodeDefinition(
                node_id="node_sandbox",
                node_type="tool",
                target="python_sandbox",
                dependencies=["node_codegen"],
            ))
            nodes.append(DAGNodeDefinition(
                node_id="node_validation",
                node_type="validation",
                target="code_validator",
                dependencies=["node_sandbox"],
            ))
        else:
            # Single-step direct execution
            nodes.append(DAGNodeDefinition(
                node_id="node_primary",
                node_type="agent",
                target=task_type,
                dependencies=[],
            ))
            nodes.append(DAGNodeDefinition(
                node_id="node_validation",
                node_type="validation",
                target=validator_chain[0] if validator_chain else "text",
                dependencies=["node_primary"],
            ))

        return nodes


# Compatibility alias
Planner = ExecutionPlanner

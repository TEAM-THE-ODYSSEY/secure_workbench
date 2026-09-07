from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Set
from .base import BaseAgent
from ..models.capabilities import TaskCapability
from ..tools.pid_tool import PIDTool, PIDToolResult


class PIDAgent(BaseAgent):
    """Specialized Industrial P&ID Agent.
    
    Translates engineering drawings into verified topological graphs,
    associates coordinate evidence bounding boxes, and performs grounded reasoning.
    """
    name = "pid"
    task_types = ["pid"]
    capabilities: Set[str] = {
        TaskCapability.VISION.value,
        TaskCapability.OCR.value,
        TaskCapability.PID_ANALYSIS.value,
        TaskCapability.TOPOLOGY.value,
        TaskCapability.EVIDENCE.value,
        TaskCapability.STRUCTURED_OUTPUT.value,
    }
    input_types = ["image", "png", "jpg", "tiff"]
    output_types = ["text", "json", "xlsx"]
    required_tools = ["ocr", "pid_engine"]
    validator_chain = ["evidence", "topology", "output"]

    def __init__(self, llm):
        super().__init__(llm)
        self.pid_tool = PIDTool()

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
        file_path = metadata.get("file_path") or metadata.get("plan", {}).get("file_path")
        plan = metadata.get("plan", {})
        output_type = plan.get("output_type", "text")
        want_excel = output_type in {"xlsx", "excel", "csv"}

        if not file_path:
            return {
                "answer": "P&ID analysis requires an engineering drawing image file.",
                "execution_result": None,
                "evidence": [],
                "warnings": ["No image file provided for P&ID analysis."],
            }

        pid_result: PIDToolResult = self.pid_tool.analyze(
            image_path=file_path,
            generate_excel=want_excel,
            output_dir="./data/outputs",
        )

        if not pid_result.success:
            return {
                "answer": f"P&ID Domain Analysis Failed: {pid_result.error}",
                "execution_result": pid_result,
                "evidence": [],
                "warnings": [f"Analysis failure: {pid_result.error}"],
            }

        # Format evidence records (Section 22)
        evidence_records = [
            {
                "claim": f"{obj['tag']} ({obj['type']}) detected",
                "evidence": {
                    "source": "pid_engine",
                    "bbox": obj.get("bbox", []),
                    "ocr": obj["tag"],
                    "confidence": obj["confidence"],
                }
            }
            for obj in pid_result.objects
        ]

        # Grounded LLM reasoning if user requested a specific query
        has_specific_question = bool(directive.strip()) and not any(
            x in directive.lower() for x in ("analyze", "process this", "run analysis", "[file")
        )

        answer_text = pid_result.summary
        if has_specific_question and self.llm:
            prompt = f"""You are a certified chemical process & piping engineer analyzing a P&ID drawing.
Answer the user question strictly using the verified topological graph and evidence detections.
Do NOT hallucinate connections that are not listed in the verified topology.

USER QUESTION:
{directive}

VERIFIED TOPOLOGY CONNECTIONS:
{json.dumps(pid_result.relationships[:35], indent=2)}

DETECTED EQUIPMENT & INSTRUMENTS:
{json.dumps(pid_result.objects[:35], indent=2)}

ANALYSIS SUMMARY:
{pid_result.summary}

PROVIDE A CONCISE, EVIDENCE-BACKED ANSWER:
"""
            try:
                llm_response = self.llm.generate(prompt=prompt, model=model)
                answer_text = f"{llm_response.strip()}\n\n---\n{pid_result.summary}"
            except Exception:
                pass

        if pid_result.xlsx_path:
            answer_text += f"\n\n**Generated Excel Workbook**: `{pid_result.xlsx_path}`"

        return {
            "answer": answer_text,
            "execution_result": pid_result,
            "evidence": evidence_records,
            "warnings": pid_result.warnings,
        }

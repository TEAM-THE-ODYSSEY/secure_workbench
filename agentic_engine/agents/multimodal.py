from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from .base import BaseAgent
from ..tools.pid_tool import PIDTool, PIDToolResult


class MultimodalAgent(BaseAgent):
    """Agent 5 — Multimodal / Document Agent.
    
    Handles heterogeneous non-plain-text inputs:
    - Structured documents: PDF, DOCX, XLSX, PPTX
    - Scanned documents and visual charts
    - P&ID schematics (delegates to specialized P&ID Domain Engine)
    """

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
        metadata = metadata or {}
        state = metadata.get("state", {})
        file_path = state.get("file_path") or metadata.get("file_path")
        plan = state.get("plan", {})
        task_type = plan.get("task_type", "")
        output_type = plan.get("output_type", "text")

        # 1. Check if this is a P&ID task
        is_pid_task = task_type == "pid" or (
            file_path and "pid" in str(file_path).lower()
        )

        if is_pid_task and file_path:
            return self._handle_pid_task(file_path, user_text, model, output_type, metadata)

        # 2. Handle general document / multimodal extraction
        return self._handle_document_task(user_text, context, file_path, model, metadata)

    def _handle_pid_task(
        self,
        file_path: str,
        user_text: str,
        model: str,
        output_type: str,
        metadata: dict[str, Any],
    ) -> str:
        want_excel = output_type in {"xlsx", "excel", "csv"}
        pid_result: PIDToolResult = self.pid_tool.analyze(
            file_path,
            generate_excel=want_excel,
            output_dir="./data/outputs",
        )

        # Store pid_result on the execution state so validators can inspect evidence & confidence
        if "state_ref" in metadata and hasattr(metadata["state_ref"], "execution_result"):
            metadata["state_ref"].execution_result = pid_result

        if not pid_result.success:
            return f"P&ID Domain Analysis Failed: {pid_result.error}"

        # If user asked a specific question about the P&ID, reason over the structured graph
        has_specific_question = bool(user_text.strip()) and not any(
            x in user_text.lower() for x in ("analyze", "process this", "run analysis", "[file")
        )

        if has_specific_question and self.llm:
            prompt = f"""You are a certified chemical process & piping engineer analyzing a P&ID drawing.
Answer the user question strictly using the verified topological graph and evidence detections.
Do NOT hallucinate connections that are not listed in the verified topology.
If confidence is low or evidence is ambiguous, explicitly state that physical verification is required.

USER QUESTION:
{user_text}

VERIFIED TOPOLOGY CONNECTIONS:
{json.dumps(pid_result.relationships[:40], indent=2)}

DETECTED EQUIPMENT & INSTRUMENTS:
{json.dumps(pid_result.objects[:40], indent=2)}

ANALYSIS SUMMARY:
{pid_result.summary}

PROVIDE A CONCISE, EVIDENCE-BACKED ENGINEERING ANSWER:
"""
            try:
                llm_response = self.llm.generate(prompt=prompt, model=model)
                combined = f"{llm_response.strip()}\n\n---\n{pid_result.summary}"
                if pid_result.xlsx_path:
                    combined += f"\n\n**Generated Excel Workbook**: `{pid_result.xlsx_path}`"
                return combined
            except Exception:
                pass

        out = pid_result.summary
        if pid_result.xlsx_path:
            out += f"\n\n**Generated Excel Workbook**: `{pid_result.xlsx_path}`"
        return out

    def _handle_document_task(
        self,
        user_text: str,
        context: str,
        file_path: Optional[str],
        model: str,
        metadata: dict[str, Any],
    ) -> str:
        prompt = f"""You are an enterprise document analysis and extraction specialist.
Analyze the provided document context, preserving document hierarchy, table associations, equipment tags, and section headers.
Answer the user's request accurately and thoroughly.

USER REQUEST:
{user_text}

DOCUMENT CONTEXT:
{context if context else 'No document context provided.'}

STRUCTURED EXTRACTION & SYNTHESIS:
"""
        if self.llm:
            try:
                return self.llm.generate(prompt=prompt, model=model)
            except Exception as e:
                return f"Document extraction completed. Content preview:\n\n{context[:1000]}"
        return f"Document extraction completed. Content:\n\n{context[:1500]}"

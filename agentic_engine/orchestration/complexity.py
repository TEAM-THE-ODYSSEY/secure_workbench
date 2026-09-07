from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Dict


@dataclass
class ComplexityMetrics:
    reasoning_depth: int = 1       # 0 (trivial), 1 (direct), 2 (multi-step), 3 (deep analytical)
    context_size: int = 0          # characters in context
    tool_complexity: int = 0       # 0 (no tools), 1 (simple query), 2 (sandbox/parser), 3 (cv pipeline)
    retrieval_complexity: int = 0  # 0 (none), 1 (simple), 2 (hybrid dense+fts+rerank)
    multimodal_complexity: int = 0 # 0 (text), 1 (doc layout), 2 (chart/diagram), 3 (dense P&ID)
    output_complexity: int = 1     # 1 (text/json), 2 (multi-sheet Excel, formal PDF)
    overall: str = "medium"        # "small", "medium", "large"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MultiDimensionalComplexityAnalyzer:
    """Evaluates task complexity across multiple orthogonal dimensions rather than relying
    on a simplistic text length threshold.
    """

    def analyze(
        self,
        text: str,
        context_chars: int = 0,
        has_file: bool = False,
        file_path: str | None = None,
        task_type: str = "reasoning",
    ) -> ComplexityMetrics:
        t = (text or "").lower()
        file_ext = (file_path or "").split(".")[-1].lower() if file_path else ""

        # 1. Reasoning Depth
        if re.search(r"\b(hi|hello|hey|ping|test)\b", t) and len(t) < 15:
            reasoning_depth = 0
        elif re.search(r"\b(solve|calculate|compare|analyze|evaluate|design|root cause|failure mode)\b", t):
            reasoning_depth = 2 if len(t) < 300 else 3
        elif re.search(r"\b(explain|what is|how does|list|describe)\b", t):
            reasoning_depth = 1
        else:
            reasoning_depth = 1

        # 2. Tool Complexity
        if task_type == "pid" or "pid" in t or file_ext in {"png", "jpg", "jpeg", "tiff", "bmp"}:
            tool_complexity = 3
        elif task_type == "coding" or re.search(r"\b(code|python|script|sandbox|run)\b", t):
            tool_complexity = 2
        elif task_type == "document" or file_ext in {"pdf", "docx", "xlsx"}:
            tool_complexity = 2
        elif re.search(r"\b(search|find|retrieve|look up)\b", t):
            tool_complexity = 1
        else:
            tool_complexity = 0

        # 3. Retrieval Complexity
        if any(x in t for x in ("company policy", "sop", "shutdown", "mrpl", "knowledge base", "internal procedure")):
            retrieval_complexity = 2
        elif any(x in t for x in ("search", "find", "reference")):
            retrieval_complexity = 1
        else:
            retrieval_complexity = 0

        # 4. Multimodal Complexity
        if file_ext in {"png", "jpg", "jpeg", "tiff", "bmp"} and (task_type == "pid" or "pid" in t):
            multimodal_complexity = 3
        elif file_ext in {"png", "jpg", "jpeg"}:
            multimodal_complexity = 2
        elif file_ext in {"pdf", "docx", "xlsx"}:
            multimodal_complexity = 1
        else:
            multimodal_complexity = 0

        # 5. Output Complexity
        if any(x in t for x in ("excel", "xlsx", "reportlab", "pdf", "multi-sheet", "workbook")):
            output_complexity = 2
        elif any(x in t for x in ("json", "csv")):
            output_complexity = 1
        else:
            output_complexity = 1

        # Calculate weighted overall score
        total_score = (
            (reasoning_depth * 2)
            + (tool_complexity * 2)
            + (multimodal_complexity * 3)
            + (retrieval_complexity * 1.5)
            + (output_complexity * 1)
            + (1 if context_chars > 3000 else 0)
        )

        if total_score <= 4 and context_chars < 1500 and tool_complexity <= 1:
            overall = "small"
        elif total_score >= 9 or multimodal_complexity >= 3 or context_chars > 8000:
            overall = "large"
        else:
            overall = "medium"

        return ComplexityMetrics(
            reasoning_depth=reasoning_depth,
            context_size=context_chars,
            tool_complexity=tool_complexity,
            retrieval_complexity=retrieval_complexity,
            multimodal_complexity=multimodal_complexity,
            output_complexity=output_complexity,
            overall=overall,
        )


# Backward compatibility alias
ComplexityAnalyzer = MultiDimensionalComplexityAnalyzer

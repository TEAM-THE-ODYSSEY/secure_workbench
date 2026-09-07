from __future__ import annotations

from enum import Enum
from typing import Set


class ModelCapability(str, Enum):
    REASONING = "reasoning"
    ANALYSIS = "analysis"
    MATHEMATICS = "mathematics"
    SYMBOLIC_MATH = "symbolic_math"
    CODING = "coding"
    CODE_REASONING = "code_reasoning"
    PYTHON = "python"
    DOCUMENT = "document"
    EXTRACTION = "extraction"
    VISION = "vision"
    MULTIMODAL = "multimodal"
    DIAGRAM_UNDERSTANDING = "diagram_understanding"
    PID_ANALYSIS = "pid_analysis"
    STRUCTURED_OUTPUT = "structured_output"
    TOOL_CALLING = "tool_calling"


class TaskCapability(str, Enum):
    REASONING = "reasoning"
    MATHEMATICS = "mathematics"
    CODING = "coding"
    DOCUMENT = "document"
    MULTIMODAL = "multimodal"
    VISION = "vision"
    OCR = "ocr"
    PID_ANALYSIS = "pid_analysis"
    TOPOLOGY = "topology"
    EVIDENCE = "evidence"
    SANDBOX = "sandbox"
    RETRIEVAL = "retrieval"
    STRUCTURED_OUTPUT = "structured_output"

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class ModelInfo:
    name: str
    capabilities: List[str] = field(default_factory=list)
    quality: int = 5
    speed: int = 5
    context: int = 8192
    priority: int = 1
    parameters: str = "7B"


MODEL_REGISTRY: Dict[str, List[ModelInfo]] = {
    "reasoning": [
        ModelInfo(
            name="qwen2.5:7b",
            capabilities=["reasoning", "general", "analysis"],
            quality=8,
            speed=7,
            context=32768,
            priority=10,
            parameters="7B",
        ),
        ModelInfo(
            name="deepseek-r1:7b",
            capabilities=["reasoning", "chain_of_thought"],
            quality=9,
            speed=6,
            context=32768,
            priority=8,
            parameters="7B",
        ),
        ModelInfo(
            name="llama3.1:8b",
            capabilities=["reasoning", "general"],
            quality=8,
            speed=7,
            context=8192,
            priority=7,
            parameters="8B",
        ),
    ],
    "mathematical": [
        ModelInfo(
            name="qwen2.5-math:7b",
            capabilities=["math", "symbolic", "numerical"],
            quality=9,
            speed=8,
            context=32768,
            priority=10,
            parameters="7B",
        ),
        ModelInfo(
            name="qwen2.5:7b",
            capabilities=["math", "general"],
            quality=8,
            speed=7,
            context=32768,
            priority=8,
            parameters="7B",
        ),
    ],
    "coding": [
        ModelInfo(
            name="qwen2.5-coder:7b",
            capabilities=["coding", "debugging", "python"],
            quality=9,
            speed=8,
            context=32768,
            priority=10,
            parameters="7B",
        ),
        ModelInfo(
            name="codellama:7b",
            capabilities=["coding", "python"],
            quality=7,
            speed=7,
            context=16384,
            priority=7,
            parameters="7B",
        ),
    ],
    "multimodal": [
        ModelInfo(
            name="qwen2-vl:7b",
            capabilities=["vision", "multimodal", "diagrams", "ocr"],
            quality=9,
            speed=7,
            context=32768,
            priority=10,
            parameters="7B",
        ),
        ModelInfo(
            name="llava:7b",
            capabilities=["vision", "multimodal"],
            quality=8,
            speed=8,
            context=8192,
            priority=8,
            parameters="7B",
        ),
        ModelInfo(
            name="qwen2.5:7b",
            capabilities=["document", "general"],
            quality=8,
            speed=8,
            context=32768,
            priority=6,
            parameters="7B",
        ),
    ],
    "document": [
        ModelInfo(
            name="qwen2.5:7b",
            capabilities=["document", "reasoning", "extraction"],
            quality=9,
            speed=8,
            context=32768,
            priority=10,
            parameters="7B",
        ),
        ModelInfo(
            name="llama3.1:8b",
            capabilities=["document", "reasoning"],
            quality=8,
            speed=7,
            context=8192,
            priority=8,
            parameters="8B",
        ),
    ],
    "pid": [
        ModelInfo(
            name="qwen2-vl:7b",
            capabilities=["vision", "schematics", "topology"],
            quality=9,
            speed=7,
            context=32768,
            priority=10,
            parameters="7B",
        ),
        ModelInfo(
            name="qwen2.5:7b",
            capabilities=["graph_reasoning", "industrial"],
            quality=9,
            speed=8,
            context=32768,
            priority=8,
            parameters="7B",
        ),
    ],
}


from dataclasses import dataclass
from typing import Dict, List, Tuple

@dataclass
class ModelInfo:
    name: str
    capabilities: List[str]
    quality: int
    speed: int
    context: int
    priority: int
    parameters: str

MODEL_REGISTRY: Dict[str, Tuple[ModelInfo, ...]] = {
    "reasoning": (
        ModelInfo(name="llama3.1:8b-instruct", capabilities=["reasoning", "document"], quality=9, speed=8, context=8192, priority=1, parameters="8B"),
        ModelInfo(name="Qwen3-4B", capabilities=["reasoning"], quality=8, speed=9, context=8192, priority=2, parameters="4B"),
    ),
    "coding": (
        ModelInfo(name="qwen2.5-coder:7b", capabilities=["coding"], quality=9, speed=8, context=32768, priority=1, parameters="7B"),
    ),
    "simple": (
        ModelInfo(name="llama3.1:8b", capabilities=["chat"], quality=8, speed=9, context=8192, priority=1, parameters="8B"),
    ),
}

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set
from .capabilities import ModelCapability


@dataclass
class ModelProfile:
    """Formal Model Profile exposing capabilities, hardware requirements, and health."""
    model_id: str
    name: str
    provider: str = "local"
    backend: str = "ollama"
    capabilities: Set[str] = field(default_factory=set)
    modalities: List[str] = field(default_factory=lambda: ["text"])
    context_length: int = 32768
    parameter_count: str = "7B"
    quantization: str = "q4_k_m"
    vram_requirement_mb: int = 4096
    max_concurrency: int = 4
    priority: int = 1
    quality: int = 8
    speed: int = 7
    health: str = "healthy"
    enabled: bool = True
    endpoint: str = "http://localhost:11434"

    # Compatibility attributes
    @property
    def context(self) -> int:
        return self.context_length

    @property
    def parameters(self) -> str:
        return self.parameter_count


# Compatibility alias
ModelInfo = ModelProfile


CANONICAL_MODEL_PROFILES: List[ModelProfile] = [
    # --- Reasoning Models ---
    ModelProfile(
        model_id="tinyllama:latest",
        name="tinyllama:latest",
        provider="local",
        backend="ollama",
        capabilities={
            ModelCapability.REASONING.value,
            ModelCapability.ANALYSIS.value,
        },
        modalities=["text"],
        context_length=2048,
        parameter_count="1.1B",
        quantization="q4_k_m",
        vram_requirement_mb=1024,
        quality=6,
        speed=10,
        priority=5,
    ),
    ModelProfile(
        model_id="qwen2.5:7b",
        name="qwen2.5:7b",
        provider="local",
        backend="ollama",
        capabilities={
            ModelCapability.REASONING.value,
            ModelCapability.ANALYSIS.value,
            ModelCapability.DOCUMENT.value,
            ModelCapability.STRUCTURED_OUTPUT.value,
        },
        modalities=["text"],
        context_length=32768,
        parameter_count="7B",
        quantization="q4_k_m",
        vram_requirement_mb=4600,
        quality=9,
        speed=8,
        priority=10,
    ),
    ModelProfile(
        model_id="deepseek-r1:7b",
        name="deepseek-r1:7b",
        provider="local",
        backend="ollama",
        capabilities={
            ModelCapability.REASONING.value,
            ModelCapability.ANALYSIS.value,
            ModelCapability.MATHEMATICS.value,
        },
        modalities=["text"],
        context_length=32768,
        parameter_count="7B",
        quantization="q4_k_m",
        vram_requirement_mb=4800,
        quality=9,
        speed=6,
        priority=9,
    ),
    ModelProfile(
        model_id="llama3.1:8b",
        name="llama3.1:8b",
        provider="local",
        backend="ollama",
        capabilities={
            ModelCapability.REASONING.value,
            ModelCapability.ANALYSIS.value,
            ModelCapability.DOCUMENT.value,
        },
        modalities=["text"],
        context_length=8192,
        parameter_count="8B",
        quantization="q4_k_m",
        vram_requirement_mb=5200,
        quality=8,
        speed=7,
        priority=8,
    ),

    # --- Mathematics Models ---
    ModelProfile(
        model_id="qwen2.5-math:7b",
        name="qwen2.5-math:7b",
        provider="local",
        backend="ollama",
        capabilities={
            ModelCapability.MATHEMATICS.value,
            ModelCapability.SYMBOLIC_MATH.value,
            ModelCapability.REASONING.value,
        },
        modalities=["text"],
        context_length=32768,
        parameter_count="7B",
        quantization="q4_k_m",
        vram_requirement_mb=4600,
        quality=10,
        speed=8,
        priority=10,
    ),

    # --- Coding Models ---
    ModelProfile(
        model_id="qwen2.5-coder:7b",
        name="qwen2.5-coder:7b",
        provider="local",
        backend="ollama",
        capabilities={
            ModelCapability.CODING.value,
            ModelCapability.CODE_REASONING.value,
            ModelCapability.PYTHON.value,
            ModelCapability.STRUCTURED_OUTPUT.value,
        },
        modalities=["text"],
        context_length=32768,
        parameter_count="7B",
        quantization="q4_k_m",
        vram_requirement_mb=4600,
        quality=10,
        speed=8,
        priority=10,
    ),
    ModelProfile(
        model_id="codellama:7b",
        name="codellama:7b",
        provider="local",
        backend="ollama",
        capabilities={
            ModelCapability.CODING.value,
            ModelCapability.PYTHON.value,
        },
        modalities=["text"],
        context_length=16384,
        parameter_count="7B",
        quantization="q4_k_m",
        vram_requirement_mb=4600,
        quality=7,
        speed=7,
        priority=7,
    ),

    # --- Vision & Multimodal Models ---
    ModelProfile(
        model_id="qwen2-vl:7b",
        name="qwen2-vl:7b",
        provider="local",
        backend="ollama",
        capabilities={
            ModelCapability.VISION.value,
            ModelCapability.MULTIMODAL.value,
            ModelCapability.DIAGRAM_UNDERSTANDING.value,
            ModelCapability.PID_ANALYSIS.value,
            ModelCapability.DOCUMENT.value,
        },
        modalities=["text", "image"],
        context_length=32768,
        parameter_count="7B",
        quantization="q4_k_m",
        vram_requirement_mb=5800,
        quality=9,
        speed=6,
        priority=10,
    ),
    ModelProfile(
        model_id="llava:7b",
        name="llava:7b",
        provider="local",
        backend="ollama",
        capabilities={
            ModelCapability.VISION.value,
            ModelCapability.MULTIMODAL.value,
        },
        modalities=["text", "image"],
        context_length=8192,
        parameter_count="7B",
        quantization="q4_k_m",
        vram_requirement_mb=5200,
        quality=8,
        speed=7,
        priority=8,
    ),
]


# Backward-compatible map for legacy consumers
MODEL_REGISTRY: Dict[str, List[ModelProfile]] = {
    "reasoning": [m for m in CANONICAL_MODEL_PROFILES if ModelCapability.REASONING.value in m.capabilities],
    "mathematical": [m for m in CANONICAL_MODEL_PROFILES if ModelCapability.MATHEMATICS.value in m.capabilities],
    "coding": [m for m in CANONICAL_MODEL_PROFILES if ModelCapability.CODING.value in m.capabilities],
    "multimodal": [m for m in CANONICAL_MODEL_PROFILES if ModelCapability.VISION.value in m.capabilities],
    "document": [m for m in CANONICAL_MODEL_PROFILES if ModelCapability.DOCUMENT.value in m.capabilities],
    "pid": [m for m in CANONICAL_MODEL_PROFILES if ModelCapability.PID_ANALYSIS.value in m.capabilities or ModelCapability.VISION.value in m.capabilities],
}

from __future__ import annotations

import logging
import subprocess
from typing import List, Optional, Set

from .capabilities import ModelCapability
from .registry import CANONICAL_MODEL_PROFILES, ModelProfile
from .resources import ResourceMonitor, ResourceSnapshot

logger = logging.getLogger("agentic_engine.model_selector")


class ModelCapabilityUnavailableError(RuntimeError):
    """Raised when no installed model possesses the required capabilities or resources."""
    pass


class ModelSelector:
    """Capability-safe and resource-aware model selector."""

    def __init__(self, resource_monitor: Optional[ResourceMonitor] = None):
        self.resources = resource_monitor or ResourceMonitor()
        self._installed_cache: Optional[Set[str]] = None

    def installed_models(self) -> Set[str]:
        if self._installed_cache is not None:
            return self._installed_cache
        names: Set[str] = set()
        try:
            out = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=3)
            if out.returncode == 0:
                for line in out.stdout.splitlines()[1:]:
                    parts = line.split()
                    if parts:
                        names.add(parts[0])
        except Exception:
            pass
        self._installed_cache = names
        return names

    @staticmethod
    def _family(name: str) -> str:
        return name.split(":", 1)[0].lower()

    def select_by_capabilities(
        self,
        required_capabilities: Set[str],
        required_modalities: Optional[List[str]] = None,
        required_context: int = 0,
        complexity: str = "medium",
    ) -> ModelProfile:
        required_modalities = required_modalities or ["text"]
        installed = self.installed_models()

        # 1. Filter candidates by capability subset: required ⊆ model.capabilities
        candidates = [
            m for m in CANONICAL_MODEL_PROFILES
            if required_capabilities.issubset(m.capabilities)
            and all(mod in m.modalities for mod in required_modalities)
            and m.context_length >= required_context
            and m.enabled
        ]

        if not candidates:
            # Try relaxed capability match if multiple capabilities specified
            candidates = [
                m for m in CANONICAL_MODEL_PROFILES
                if len(required_capabilities.intersection(m.capabilities)) > 0
                and all(mod in m.modalities for mod in required_modalities)
                and m.context_length >= required_context
                and m.enabled
            ]

        if not candidates:
            raise ModelCapabilityUnavailableError(
                f"MODEL_CAPABILITY_UNAVAILABLE: No configured model satisfies required capabilities "
                f"{required_capabilities} with modalities {required_modalities} and context {required_context}."
            )

        # 2. Check installed status in Ollama (if any models are installed)
        if installed:
            installed_candidates = [
                m for m in candidates
                if m.name in installed or self._family(m.name) in {self._family(x) for x in installed}
            ]
            if installed_candidates:
                candidates = installed_candidates
            else:
                # None of the qualified models are installed
                raise ModelCapabilityUnavailableError(
                    f"MODEL_CAPABILITY_UNAVAILABLE: Qualified models {[m.name for m in candidates]} "
                    f"for capabilities {required_capabilities} are not installed in Ollama."
                )

        # 3. Check hardware resources (VRAM / RAM)
        resource_snapshot = self.resources.get_snapshot()
        resource_qualified = [
            m for m in candidates
            if not resource_snapshot.has_cuda or resource_snapshot.vram_available_mb >= m.vram_requirement_mb
        ]
        if resource_qualified:
            candidates = resource_qualified

        # 4. Rank candidates by complexity score
        if complexity == "small":
            score_fn = lambda m: (m.speed, m.priority, m.quality)
        elif complexity == "large":
            score_fn = lambda m: (m.quality, m.context_length, m.priority)
        else:
            score_fn = lambda m: (m.quality, m.speed, m.priority)

        candidates.sort(key=score_fn, reverse=True)
        return candidates[0]

    def select(self, task_type: str, complexity: str = "medium", required_context: int = 0) -> ModelProfile:
        """Legacy compatibility wrapper for task_type."""
        cap_map = {
            "reasoning": {ModelCapability.REASONING.value},
            "mathematical": {ModelCapability.MATHEMATICS.value},
            "coding": {ModelCapability.CODING.value},
            "multimodal": {ModelCapability.VISION.value},
            "document": {ModelCapability.DOCUMENT.value},
            "pid": {ModelCapability.PID_ANALYSIS.value, ModelCapability.VISION.value},
        }
        caps = cap_map.get(task_type.lower(), {ModelCapability.REASONING.value})
        modalities = ["text", "image"] if task_type.lower() in {"multimodal", "pid"} else ["text"]
        try:
            return self.select_by_capabilities(
                required_capabilities=caps,
                required_modalities=modalities,
                required_context=required_context,
                complexity=complexity,
            )
        except ModelCapabilityUnavailableError:
            # If vision model unavailable for PID, allow fall back to general document reasoning if text-only
            if task_type.lower() == "pid":
                return self.select_by_capabilities(
                    required_capabilities={ModelCapability.REASONING.value},
                    required_modalities=["text"],
                    required_context=required_context,
                    complexity=complexity,
                )
            raise

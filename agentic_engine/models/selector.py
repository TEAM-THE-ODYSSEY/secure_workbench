from __future__ import annotations

import random
import subprocess

from .registry import MODEL_REGISTRY, ModelInfo


class ModelSelector:
    """Select a configured local model, preferring models actually installed in Ollama."""

    def __init__(self):
        self._installed_cache: set[str] | None = None

    def installed_models(self) -> set[str]:
        if self._installed_cache is not None:
            return self._installed_cache
        names: set[str] = set()
        try:
            out = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=5)
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

    def select(self, task_type: str, complexity: str = "medium", required_context: int = 0) -> ModelInfo:
        candidates = list(MODEL_REGISTRY.get(task_type, MODEL_REGISTRY["reasoning"]))
        candidates = [m for m in candidates if m.context >= required_context] or candidates

        installed = self.installed_models()
        if installed:
            exact = [m for m in candidates if m.name in installed]
            family = [m for m in candidates if self._family(m.name) in {self._family(x) for x in installed}]
            if exact:
                candidates = exact
            elif family:
                # Use the installed tag if it belongs to a configured family.
                candidates = [
                    ModelInfo(
                        name=next(x for x in installed if self._family(x) == self._family(m.name)),
                        capabilities=m.capabilities, quality=m.quality, speed=m.speed,
                        context=m.context, priority=m.priority, parameters=m.parameters,
                    ) for m in family
                ]
            else:
                # If no configured model from this category is installed, fall back to installed general models
                general_installed = [m for m in MODEL_REGISTRY["reasoning"] if m.name in installed]
                if general_installed:
                    candidates = general_installed
                elif installed:
                    first_installed = sorted(list(installed))[0]
                    candidates = [ModelInfo(name=first_installed, capabilities=["general"], quality=7, speed=7, context=8192, priority=5, parameters="7B")]
                else:
                    raise RuntimeError(f"No configured {task_type} model is installed in Ollama.")

        if complexity == "small":
            score = lambda m: (m.speed, m.priority, m.quality)
        elif complexity == "large":
            score = lambda m: (m.quality, m.context, m.priority)
        else:
            score = lambda m: (m.quality, m.speed, m.priority)

        best_key = max(score(m) for m in candidates)
        return random.choice([m for m in candidates if score(m) == best_key])

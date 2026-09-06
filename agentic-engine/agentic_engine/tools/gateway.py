"""
OllamaGateway
--------------
Single choke point for all LLM inference in the engine.

Every agent talks to models THROUGH this class, never directly to the
`ollama` package. That keeps the "swap models later without redesigning
agents" requirement real: change the default model / add retries /
add a different local backend here, and every agent picks it up for
free.

No external network calls are made — `ollama` talks to a local Ollama
daemon (default http://localhost:11434) which itself only serves
models you have pulled with `ollama pull <model>`.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import ollama


class OllamaGatewayError(RuntimeError):
    pass


class OllamaGateway:
    def __init__(
        self,
        default_model: str = "llama3.1",
        host: Optional[str] = None,
        request_timeout: int = 120,
    ):
        """
        default_model: any model you've pulled locally, e.g.
            `ollama pull llama3.1`
        host: override if Ollama runs on a non-default host/port,
            e.g. "http://127.0.0.1:11434". None uses the ollama
            package's own default.
        """
        self.default_model = default_model
        self._client = ollama.Client(host=host) if host else ollama.Client()
        self.request_timeout = request_timeout

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        temperature: float = 0.2,
    ) -> str:
        """
        messages: list of {"role": "system"|"user"|"assistant", "content": str}
        Returns the assistant's text content.
        """
        opts = {"temperature": temperature}
        if options:
            opts.update(options)

        try:
            response = self._client.chat(
                model=model or self.default_model,
                messages=messages,
                options=opts,
            )
        except Exception as exc:  # ollama raises its own error types
            raise OllamaGatewayError(
                f"Ollama chat call failed (model={model or self.default_model}): {exc}. "
                "Is the Ollama daemon running (`ollama serve`) and is the model pulled "
                "(`ollama pull <model>`)?"
            ) from exc

        try:
            return response["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise OllamaGatewayError(f"Unexpected Ollama response shape: {response}") from exc

    def list_local_models(self) -> List[str]:
        try:
            data = self._client.list()
            return [m.get("model") or m.get("name") for m in data.get("models", [])]
        except Exception as exc:
            raise OllamaGatewayError(f"Could not list local Ollama models: {exc}") from exc

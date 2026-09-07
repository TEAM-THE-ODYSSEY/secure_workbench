"""
OpenAI-compatible vLLM Client for Qwen3-4B primary and Qwen3-1.7B fallback.
"""

import logging
import time
import requests
from typing import Any, Dict, List, Optional
from rag.config import config

logger = logging.getLogger("agent.models.vllm_client")


class VLLMClient:
    """
    HTTP Client for vLLM server providing OpenAI API compatible chat endpoints.
    """

    def __init__(self, api_base: Optional[str] = None, timeout_seconds: float = 30.0):
        self.api_base = (api_base or config.VLLM_API_BASE).rstrip("/")
        self.timeout = timeout_seconds

    def health_check(self) -> bool:
        """Check if vLLM server endpoint is available."""
        try:
            url = f"{self.api_base}/models"
            resp = requests.get(url, timeout=3.0)
            return resp.status_code == 200
        except Exception:
            return False

    def generate_chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "Qwen3-4B",
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> Dict[str, Any]:
        """
        Send chat completion request to vLLM OpenAI compatible endpoint.
        Returns response dict with content, latency_ms, model, and token usage.
        """
        url = f"{self.api_base}/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        start_time = time.time()
        try:
            resp = requests.post(url, json=payload, timeout=self.timeout)
            latency_ms = round((time.time() - start_time) * 1000, 2)

            if resp.status_code != 200:
                raise RuntimeError(f"vLLM API returned HTTP {resp.status_code}: {resp.text}")

            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})

            return {
                "content": content,
                "model": data.get("model", model),
                "latency_ms": latency_ms,
                "usage": usage,
            }
        except Exception as e:
            latency_ms = round((time.time() - start_time) * 1000, 2)
            logger.error(f"vLLM request failed (model={model}, latency={latency_ms}ms): {e}")
            raise RuntimeError(f"vLLM API failure ({model}): {str(e)}") from e

"""
Model Manager abstraction for the Reasoning Mini-Agent V1.
Provides automated infrastructure failover from Primary (Qwen3-4B) to Fallback (Qwen3-1.7B).
"""

import json
import logging
import os
import time
from typing import Any, Dict, Optional, Type, TypeVar
import httpx
from pydantic import BaseModel, ValidationError

from rag.config import config

logger = logging.getLogger("agent.model_manager")

T = TypeVar("T", bound=BaseModel)


class ModelManagerError(Exception):
    """Base exception for model manager errors."""
    pass


class InfrastructureError(ModelManagerError):
    """Infrastructure failure requiring fallback (connection, timeout, OOM, 5xx)."""
    pass


class QualityFailureError(ModelManagerError):
    """Quality failure (structured output schema validation error) — should NOT trigger fallback."""
    pass


class ModelManager:
    """
    Model Manager orchestrating LLM calls with automatic infrastructure failover.
    Primary: Qwen3-4B
    Fallback: Qwen3-1.7B
    """

    def __init__(
        self,
        vllm_api_base: Optional[str] = None,
        primary_model: Optional[str] = None,
        fallback_model: Optional[str] = None,
        timeout: float = 30.0,
        api_key: str = "EMPTY",
    ):
        raw_vllm_url = (
            vllm_api_base
            or os.getenv("VLLM_BASE_URL")
            or os.getenv("VLLM_API_BASE")
            or getattr(config, "VLLM_API_BASE", "http://localhost:8001/v1")
        )
        if raw_vllm_url and not raw_vllm_url.endswith("/v1") and not raw_vllm_url.endswith("/v1/"):
            raw_vllm_url = raw_vllm_url.rstrip("/") + "/v1"

        self.vllm_api_base = raw_vllm_url
        self.primary_model = primary_model or os.getenv("PRIMARY_MODEL_NAME", getattr(config, "PRIMARY_MODEL_NAME", "Qwen/Qwen2.5-1.5B-Instruct-AWQ"))
        self.fallback_model = fallback_model or os.getenv("FALLBACK_MODEL_NAME", getattr(config, "FALLBACK_MODEL_NAME", "Qwen/Qwen2.5-1.5B-Instruct-AWQ"))
        self.timeout = timeout
        self.api_key = api_key

        self.active_model = self.primary_model
        self.fallback_used = False
        self.last_failure_reason: Optional[str] = None
        self.last_latency_ms: float = 0.0

    def get_active_model(self) -> str:
        """Return currently active model name."""
        return self.active_model

    def health_check(self) -> Dict[str, Any]:
        """Check availability of primary and fallback model endpoints."""
        status = {
            "vllm_api_base": self.vllm_api_base,
            "primary_model": self.primary_model,
            "fallback_model": self.fallback_model,
            "active_model": self.active_model,
            "fallback_used": self.fallback_used,
            "status": "UNKNOWN",
        }
        try:
            with httpx.Client(timeout=3.0) as client:
                res = client.get(f"{self.vllm_api_base}/models")
                if res.status_code == 200:
                    status["status"] = "HEALTHY"
                    status["models"] = res.json()
                else:
                    status["status"] = f"DEGRADED (HTTP {res.status_code})"
        except Exception as e:
            status["status"] = f"OFFLINE ({str(e)})"
        return status

    def _call_llm_api(
        self,
        model: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> str:
        """Call OpenAI-compatible completions/chat endpoint."""
        url = f"{self.vllm_api_base.rstrip('/')}/chat/completions"
        messages = []
        sys_len = 0
        if system_prompt:
            clean_sys = system_prompt[:1000]
            sys_len = len(clean_sys)
            messages.append({"role": "system", "content": clean_sys})

        max_prompt_chars = 3500
        if len(prompt) > max_prompt_chars:
            prompt = prompt[:max_prompt_chars] + "\n...[Context truncated to fit model limit]"

        messages.append({"role": "user", "content": prompt})

        approx_prompt_tokens = int((len(prompt) + sys_len) / 2.5)
        remaining_budget = max(128, 1980 - approx_prompt_tokens)
        safe_max_tokens = min(max_tokens, remaining_budget)

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": safe_max_tokens,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, json=payload, headers=headers)
                if resp.status_code != 200:
                    raise InfrastructureError(
                        f"LLM API returned HTTP {resp.status_code}: {resp.text[:200]}"
                    )
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                return content
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError) as e:
            raise InfrastructureError(f"LLM API Infrastructure Failure ({model}): {str(e)}")
        except Exception as e:
            if isinstance(e, InfrastructureError):
                raise e
            raise InfrastructureError(f"LLM API Unexpected Error ({model}): {str(e)}")

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        task_id: Optional[str] = None,
    ) -> str:
        """
        Generate text completion with automatic primary -> fallback failover on infrastructure errors.
        """
        start_time = time.time()

        # Try primary model first
        try:
            logger.info(f"[{task_id or 'AGENT'}] Invoking Primary LLM Model: {self.primary_model}")
            result = self._call_llm_api(
                model=self.primary_model,
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            self.active_model = self.primary_model
            self.fallback_used = False
            self.last_failure_reason = None
            self.last_latency_ms = (time.time() - start_time) * 1000
            return result

        except InfrastructureError as infra_err:
            logger.warning(
                f"[{task_id or 'AGENT'}] Primary Model ({self.primary_model}) Infrastructure Failure: {infra_err}. "
                f"Attempting Fallback Model ({self.fallback_model})..."
            )
            self.last_failure_reason = str(infra_err)

            # Try fallback model
            try:
                result = self._call_llm_api(
                    model=self.fallback_model,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                self.active_model = self.fallback_model
                self.fallback_used = True
                self.last_latency_ms = (time.time() - start_time) * 1000
                logger.info(f"[{task_id or 'AGENT'}] Fallback Model ({self.fallback_model}) succeeded.")
                return result
            except InfrastructureError as fallback_err:
                logger.error(
                    f"[{task_id or 'AGENT'}] Both Primary and Fallback Models Failed: {fallback_err}"
                )
                raise InfrastructureError(
                    f"Primary model failed ({infra_err}) and Fallback model failed ({fallback_err})"
                )

    def generate_structured(
        self,
        prompt: str,
        schema_cls: Type[T],
        system_prompt: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> T:
        """
        Generate structured output validated against a Pydantic schema.
        Failure to parse JSON or validate schema is a Quality Failure, which raises QualityFailureError (no downgrade).
        """
        raw_response = self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.0,
            task_id=task_id,
        )

        # Clean JSON markdown fences if present
        clean_json = raw_response.strip()
        if clean_json.startswith("```json"):
            clean_json = clean_json[7:]
        if clean_json.startswith("```"):
            clean_json = clean_json[3:]
        if clean_json.endswith("```"):
            clean_json = clean_json[:-3]
        clean_json = clean_json.strip()

        try:
            data = json.loads(clean_json)
            # Handle explicit INSUFFICIENT_EVIDENCE reported in JSON response
            if isinstance(data, dict) and data.get("error") == "INSUFFICIENT_EVIDENCE":
                raise QualityFailureError(f"INSUFFICIENT_EVIDENCE reported: {data.get('reason', '')}")
            return schema_cls.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as err:
            logger.warning(f"[{task_id or 'AGENT'}] Structured Output Validation Failed: {err}")
            raise QualityFailureError(f"Structured output schema validation failed: {str(err)}")

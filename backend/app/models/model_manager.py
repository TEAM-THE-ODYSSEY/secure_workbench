"""
ModelManager Abstraction for Main AI Agent.
Manages primary model (Qwen3-4B) and fallback model (Qwen3-1.7B) via OpenAI-compatible vLLM API.
Enforces infrastructure-only failover, latency tracking, token metrics, and structured JSON parsing.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar
from pydantic import BaseModel, ValidationError

from agent.models.vllm_client import VLLMClient
from rag.config import config

logger = logging.getLogger("agent.models.model_manager")

T = TypeVar("T", bound=BaseModel)


class InfrastructureError(Exception):
    """Raised when an infrastructure error (timeout, OOM, server down) occurs."""
    pass


class QualityFailureError(Exception):
    """Raised when LLM output fails validation or quality checks."""
    pass


class ModelManager:
    """
    Model Server abstraction providing seamless primary (Qwen3-4B) -> fallback (Qwen3-1.7B)
    execution over vLLM.
    """

    def __init__(
        self,
        vllm_client: Optional[VLLMClient] = None,
        primary_model: str = "Qwen3-4B",
        fallback_model: str = "Qwen3-1.7B",
    ):
        self.client = vllm_client or VLLMClient()
        self.primary_model = primary_model
        self.fallback_model = fallback_model
        self.active_model = primary_model

    def health_check(self) -> Dict[str, Any]:
        """Return connectivity and active model status."""
        is_online = self.client.health_check()
        return {
            "status": "HEALTHY" if is_online else "OFFLINE",
            "active_model": self.active_model,
            "primary_model": self.primary_model,
            "fallback_model": self.fallback_model,
            "backend": "vLLM (OpenAI Compatible)",
        }

    def get_active_model(self) -> str:
        """Return the active model name."""
        return self.active_model

    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 2048,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute text generation with infrastructure-only fallback handling.
        Returns dict containing content, active_model, fallback_used, fallback_reason, latency_ms, usage.
        """
        fallback_used = False
        fallback_reason = None
        start_time = time.time()

        # Try Primary Model
        try:
            logger.info(f"[{task_id or 'global'}] Invoking Primary Model '{self.primary_model}'...")
            res = self.client.generate_chat(
                messages=messages,
                model=self.primary_model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            self.active_model = self.primary_model
            res["fallback_used"] = False
            res["fallback_reason"] = None
            return res

        except Exception as primary_exc:
            fallback_reason = f"LLM API Infrastructure Failure ({self.primary_model}): {str(primary_exc)}"
            logger.warning(f"[{task_id or 'global'}] Primary Model '{self.primary_model}' failed. Attempting Fallback '{self.fallback_model}'. Error: {primary_exc}")

        # Try Fallback Model
        try:
            res = self.client.generate_chat(
                messages=messages,
                model=self.fallback_model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            self.active_model = self.fallback_model
            fallback_used = True
            res["fallback_used"] = True
            res["fallback_reason"] = fallback_reason
            return res

        except Exception as fallback_exc:
            total_latency = round((time.time() - start_time) * 1000, 2)
            logger.error(f"[{task_id or 'global'}] Both Primary and Fallback Models Failed. Total Latency: {total_latency}ms")
            raise InfrastructureError(
                f"Primary model failed ({fallback_reason}) and Fallback model failed ({fallback_exc})."
            ) from fallback_exc

    def generate_structured(
        self,
        messages: List[Dict[str, str]],
        response_schema: Type[T],
        temperature: float = 0.1,
        max_tokens: int = 2048,
        task_id: Optional[str] = None,
    ) -> Tuple[T, Dict[str, Any]]:
        """
        Generate response and validate against target Pydantic schema.
        Returns tuple of (parsed_pydantic_object, execution_metadata_dict).
        """
        gen_res = self.generate(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            task_id=task_id,
        )

        if isinstance(gen_res, str):
            raw_text = gen_res
            meta = {"model": self.active_model, "fallback_used": False}
        else:
            raw_text = gen_res.get("content", "")
            meta = gen_res
        cleaned_json = self._extract_json_block(raw_text)

        try:
            parsed_data = json.loads(cleaned_json)
            validated_obj = response_schema.model_validate(parsed_data)
            return validated_obj, gen_res
        except (json.JSONDecodeError, ValidationError) as err:
            logger.error(f"[{task_id or 'global'}] JSON validation failed for schema {response_schema.__name__}: {err}\nRaw text: {raw_text[:300]}")
            raise QualityFailureError(f"Failed to parse LLM response into valid {response_schema.__name__} schema: {err}") from err

    def _extract_json_block(self, text: str) -> str:
        """Strip markdown ```json block code fence markers."""
        t = text.strip()
        if t.startswith("```json"):
            t = t[7:]
        elif t.startswith("```"):
            t = t[3:]
        if t.endswith("```"):
            t = t[:-3]
        return t.strip()


class Tuple_Structured_Result:
    """Type alias helper for generate_structured output signature."""
    pass

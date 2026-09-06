"""
Mock vLLM OpenAI-Compatible API Server for testing and demonstrating LLM model reasoning,
structured PDF generation, and automated primary-to-fallback model switching.
Runs on port 8080.
"""

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
import uvicorn
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] mock_vllm: %(message)s")
logger = logging.getLogger("mock_vllm")

app = FastAPI(title="Mock vLLM Server (OpenAI Compatible)")

# Flag to toggle failover simulation
SIMULATE_PRIMARY_FAILOVER = False


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list
    temperature: float = 0.0
    max_tokens: int = 2048


@app.get("/v1/models")
def list_models():
    """vLLM models listing endpoint."""
    return {
        "object": "list",
        "data": [
            {"id": "Qwen3-4B", "object": "model", "owned_by": "vllm"},
            {"id": "Qwen3-1.7B", "object": "model", "owned_by": "vllm"},
        ]
    }


@app.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest):
    """vLLM chat completions endpoint with failover simulation support."""
    logger.info(f"Received LLM completion request for model: '{req.model}'")

    # Simulate primary model infrastructure failure if enabled or if requested
    if SIMULATE_PRIMARY_FAILOVER and req.model == "Qwen3-4B":
        logger.warning(f"Simulating primary model failure for '{req.model}' (HTTP 500)...")
        raise HTTPException(status_code=500, detail="Simulated primary model CUDA out of memory / connection error")

    # Construct structured output JSON matching StructuredPDFContent schema
    user_prompt = ""
    for msg in req.messages:
        if msg.get("role") == "user":
            user_prompt = msg.get("content", "")

    structured_response = {
        "title": "Standard Operating Procedure: Crude Feed Pump P-101A",
        "purpose": "Define the startup, normal operation, and isolation sequence for Crude Feed Charge Pump P-101A in Crude Distillation Unit (CDU-1) using Qwen3 reasoning model.",
        "scope": "Applies to Operations & Maintenance personnel in CDU-1 Unit at MRPL Refinery.",
        "preconditions": [
            "Ensure suction valve HV-101 is 100% open prior to motor start.",
            "Verify lube oil level in sight glass is between 50% and 75%.",
            "Confirm mechanical seal flush cooling water flow is active (min 15 LPM)."
        ],
        "safety_requirements": [
            "Wear heat-resistant gloves, safety goggles, and personal H2S monitor.",
            "Obtain Hot Work / Operational permit from Area Superintendent."
        ],
        "procedure_steps": [
            {
                "step_number": 1,
                "instruction": "Notify Central Control Room (CCR) board operator prior to starting pump P-101A.",
                "citations": [
                    {
                        "document_id": "doc_966495bc25ff",
                        "title": "Document doc_966495bc25ff",
                        "version": "R0",
                        "section": "General",
                        "page": 1,
                        "trust_level": "TRUSTED"
                    }
                ]
            },
            {
                "step_number": 2,
                "instruction": "Crack open discharge valve XV-101 to 10% position to fill discharge piping gradually.",
                "citations": [
                    {
                        "document_id": "doc_966495bc25ff",
                        "title": "Document doc_966495bc25ff",
                        "version": "R0",
                        "section": "General",
                        "page": 1,
                        "trust_level": "TRUSTED"
                    }
                ]
            },
            {
                "step_number": 3,
                "instruction": "Press Local Start button on Motor Control Center (MCC) panel in field.",
                "citations": [
                    {
                        "document_id": "doc_966495bc25ff",
                        "title": "Document doc_966495bc25ff",
                        "version": "R0",
                        "section": "General",
                        "page": 1,
                        "trust_level": "TRUSTED"
                    }
                ]
            },
            {
                "step_number": 4,
                "instruction": "Monitor discharge pressure transmitter PIC-101 until reading stabilizes at 22.0 kg/cm2.",
                "citations": [
                    {
                        "document_id": "doc_966495bc25ff",
                        "title": "Document doc_966495bc25ff",
                        "version": "R0",
                        "section": "General",
                        "page": 1,
                        "trust_level": "TRUSTED"
                    }
                ]
            },
            {
                "step_number": 5,
                "instruction": "Gradually open discharge valve XV-101 to 100% over 5 minutes while checking seal temperature.",
                "citations": [
                    {
                        "document_id": "doc_966495bc25ff",
                        "title": "Document doc_966495bc25ff",
                        "version": "R0",
                        "section": "General",
                        "page": 1,
                        "trust_level": "TRUSTED"
                    }
                ]
            }
        ],
        "operating_limits": [
            {
                "parameter": "Maximum Operating Temperature",
                "value": "345 °C",
                "citations": [
                    {
                        "document_id": "doc_966495bc25ff",
                        "title": "Document doc_966495bc25ff",
                        "version": "R0",
                        "section": "General",
                        "page": 1,
                        "trust_level": "TRUSTED"
                    }
                ]
            },
            {
                "parameter": "Maximum Discharge Pressure",
                "value": "24.5 kg/cm2",
                "citations": [
                    {
                        "document_id": "doc_966495bc25ff",
                        "title": "Document doc_966495bc25ff",
                        "version": "R0",
                        "section": "General",
                        "page": 1,
                        "trust_level": "TRUSTED"
                    }
                ]
            }
        ],
        "warnings": [
            "DO NOT run pump P-101A dry. Ensure suction line is fully primed before starting.",
            "If vibration exceeds 4.5 mm/s, trip motor immediately and report to Maintenance."
        ],
        "references": [
            {
                "document_id": "doc_966495bc25ff",
                "title": "Document doc_966495bc25ff",
                "version": "R0",
                "section": "General",
                "page": 1,
                "trust_level": "TRUSTED"
            }
        ]
    }

    content_str = json.dumps(structured_response, indent=2)

    return {
        "id": "chatcmpl-mockvllm123",
        "object": "chat.completion",
        "created": 1700000000,
        "model": req.model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content_str
                },
                "finish_reason": "stop"
            }
        ]
    }


@app.post("/v1/test/failover")
def set_failover(enable: bool = True):
    """Control endpoint to enable/disable primary model failover simulation."""
    global SIMULATE_PRIMARY_FAILOVER
    SIMULATE_PRIMARY_FAILOVER = enable
    return {"simulate_primary_failover": SIMULATE_PRIMARY_FAILOVER}


if __name__ == "__main__":
    uvicorn.run("mock_vllm_server:app", host="0.0.0.0", port=8080)

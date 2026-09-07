"""
Mock vLLM OpenAI-Compatible API Server for testing and demonstrating LLM model reasoning,
structured PDF generation, dynamic context planning, and automated primary-to-fallback model switching.
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

    # Simulate primary model infrastructure failure if enabled
    if SIMULATE_PRIMARY_FAILOVER and req.model == "Qwen3-4B":
        logger.warning(f"Simulating primary model failure for '{req.model}' (HTTP 500)...")
        raise HTTPException(status_code=500, detail="Simulated primary model CUDA out of memory / connection error")

    # Extract user & system prompt
    full_prompt_text = ""
    user_prompt = ""
    for msg in req.messages:
        content = msg.get("content", "")
        full_prompt_text += f"\n{content}"
        if msg.get("role") == "user":
            user_prompt = content

    full_prompt_lower = full_prompt_text.lower()

    user_prompt_lower = user_prompt.lower()

    # Determine response schema based on prompt inspection
    if "contextplan" in full_prompt_lower or "context planner" in full_prompt_lower or '"intent"' in full_prompt_lower:
        # Context Plan schema
        is_pdf = any(kw in user_prompt_lower for kw in ["generate pdf", "download pdf", "export pdf", "make a pdf", "create pdf report", "generate report"])
        intent_type = "GENERAL_REASONING"
        import re
        is_doc = any(kw in user_prompt_lower for kw in ["explain", "doc", "pdf", "file", "report", "health", "safety", "award"])
        greeting_pattern = r'\b(hi|hai|hello|hey|greetings|good morning|good afternoon|good evening|how are you|how are u|how do you do|who are you|what can you do)\b'
        is_greeting = not is_doc and bool(re.search(greeting_pattern, user_prompt_lower))

        if is_greeting:
            intent_type = "GREETING"
        elif "award" in user_prompt_lower or "safety" in user_prompt_lower or "health" in user_prompt_lower or "analys" in user_prompt_lower or "explain" in user_prompt_lower or "doc" in user_prompt_lower:
            intent_type = "DOCUMENT_ANALYSIS"
        elif "fail" in user_prompt_lower or "p-101a" in user_prompt_lower:
            intent_type = "FAILURE_ANALYSIS"
        elif is_pdf:
            intent_type = "SOP_SYNTHESIS"

        response_data = {
            "intent": intent_type,
            "entities": ["P-101A"] if "p-101a" in user_prompt_lower else [],
            "required_context": ["equipment_spec", "sop", "maintenance_history", "safety_report"],
            "tool_calls": [
                {"tool": "knowledge_search", "query": user_prompt or "Safety awards"}
            ],
            "output_type": "PDF" if is_pdf else "TEXT"
        }
    elif "finalreasoningoutput" in full_prompt_lower or "reasoning_output" in full_prompt_lower or '"confidence"' in full_prompt_lower:
        # Final Reasoning Output schema
        import re
        is_doc = any(kw in user_prompt_lower for kw in ["explain", "doc", "pdf", "file", "report", "health", "safety", "award"])
        greeting_pattern = r'\b(hi|hai|hello|hey|greetings|good morning|good afternoon|good evening|how are you|how are u|how do you do|who are you|what can you do)\b'
        is_greeting = not is_doc and bool(re.search(greeting_pattern, user_prompt_lower))

        is_explicit_doc_explain = any(kw in user_prompt_lower for kw in ["explain health", "explain doc", "summarize doc", "health and safety.docx", "safety award doc"])
        is_explicit_doc_explain = any(kw in user_prompt_lower for kw in ["explain health", "explain doc", "summarize doc", "health and safety.docx", "safety award doc"])
        if is_greeting:
            answer_str = "I'm doing well, thank you for asking! I am the MRPL Sovereign AI Assistant, operating locally and securely. I can assist you with refinery operations, P&ID topology, SOP instructions, equipment failure analysis, and document searches across CDU-1 and plant assets. How can I help you today?"
        elif is_explicit_doc_explain:
            answer_str = "Based on the analysis of 'Health And Safety.docx':\n\n### 📄 Document Analysis & Summary\n- **Safety Recognition**: MRPL was honored with the **National Safety Council (NSC) Apex Safety Award** and the **Oil Industry Safety Directorate (OISD) Best Safety Performance Award**.\n- **Operational Metrics**: Over 15 million consecutive accident-free man-hours achieved across CDU-1 and processing units.\n- **Mandatory Safety Rules**: Continuous personal H2S monitor readiness, SCBA availability, and strict Buddy System compliance in processing areas."
        elif "p-101a" in user_prompt_lower or "fail" in user_prompt_lower:
            answer_str = "Crude Feed Charge Pump P-101A experienced elevated vibration levels (6.8 mm/s) on the non-drive end bearing. Technical analysis indicates bearing race pitting and mechanical seal face degradation due to thermal stress. Operational team isolated XV-101 and successfully transferred feed to standby pump P-101B."
        else:
            answer_str = (
                f"### 📊 Operational Query: **{user_prompt}**\n\n"
                f"I searched the MRPL Sovereign Knowledge Base for **{user_prompt}**.\n"
                f"- **Result**: To provide exact verified figures without hallucination, please ensure the relevant document or report is ingested into the Knowledge Base or uploaded in your chat session."
            )

        response_data = {
            "answer": answer_str,
            "claims": ["Safety awards and health performance verified against official records."],
            "citations": [],
            "confidence": "HIGH",
            "limitations": []
        }
    else:
        # Default StructuredPDFContent schema
        response_data = {
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
                            "document_id": "doc_SOP_CDU_P101A",
                            "title": "SOP-23: Pump Operating Procedure",
                            "version": "v3.0",
                            "section": "General",
                            "page": 18,
                            "trust_level": "TRUSTED"
                        }
                    ]
                },
                {
                    "step_number": 2,
                    "instruction": "Crack open discharge valve XV-101 to 10% position to fill discharge piping gradually.",
                    "citations": [
                        {
                            "document_id": "doc_SOP_CDU_P101A",
                            "title": "SOP-23: Pump Operating Procedure",
                            "version": "v3.0",
                            "section": "General",
                            "page": 18,
                            "trust_level": "TRUSTED"
                        }
                    ]
                }
            ],
            "operating_limits": [
                {
                    "parameter": "Maximum Operating Temperature",
                    "value": "345 °C",
                    "citations": []
                },
                {
                    "parameter": "Maximum Discharge Pressure",
                    "value": "24.5 kg/cm2",
                    "citations": []
                }
            ],
            "warnings": [
                "DO NOT run pump P-101A dry. Ensure suction line is fully primed before starting."
            ],
            "references": [
                {
                    "document_id": "doc_SOP_CDU_P101A",
                    "title": "SOP-23: Pump Operating Procedure",
                    "version": "v3.0",
                    "section": "General",
                    "page": 18,
                    "trust_level": "TRUSTED"
                }
            ]
        }

    content_str = json.dumps(response_data, indent=2)

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

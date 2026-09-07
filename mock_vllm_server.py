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
        
        if is_greeting or user_prompt_lower in ["hi", "hai", "hello", "hey", "who are you"]:
            answer_str = "Hello! I am the MRPL Sovereign AI Assistant, operating locally and securely. I can assist you with refinery operations, P&ID topology, SOP instructions, equipment failure analysis, and document searches across CDU-1 and plant assets. How can I help you today?"
        elif "2+2" in user_prompt_lower or "2 + 2" in user_prompt_lower:
            answer_str = "2 + 2 = 4."
        elif "centrifugal pump" in user_prompt_lower:
            answer_str = (
                "### ⚙️ Centrifugal Pump Fundamentals\n\n"
                "A **centrifugal pump** is a mechanical device designed to move fluid by converting rotational kinetic energy from a motor or turbine into hydrodynamic energy of the fluid flow.\n\n"
                "#### 🔑 Key Working Principles:\n"
                "1. **Impeller Rotation**: The high-speed impeller accelerates the fluid outward from the pump casing center (eye).\n"
                "2. **Volute Conversion**: As fluid travels through the expanding volute or diffuser casing, velocity decreases while static pressure increases.\n"
                "3. **Continuous Suction**: The pressure drop at the eye draws a continuous feed from the suction line.\n\n"
                "#### 🛡️ Operating Considerations in Refineries:\n"
                "- Maintain Adequate **NPSHa** (Net Positive Suction Head available) to prevent cavitation.\n"
                "- Monitor NDE/DE bearing vibration (< 4.0 mm/s) and seal flush cooling temperatures."
            )
        elif "explain what a refinery is" in user_prompt_lower or "what is a refinery" in user_prompt_lower:
            answer_str = (
                "### 🏭 Petroleum Refinery Overview\n\n"
                "A **petroleum refinery** is an industrial process plant where crude oil is transformed and refined into useful products such as Liquefied Petroleum Gas (LPG), Petrol (Motor Spirit), Aviation Turbine Fuel (ATF), Diesel (HSD), and Petrochemical feedstocks.\n\n"
                "#### 📌 Core Process Units:\n"
                "- **Crude Distillation Unit (CDU)**: Fractional distillation separating crude by boiling ranges.\n"
                "- **Hydrocracker Unit (HCU)**: Cracking heavy hydrocarbons into lighter, high-value fuels.\n"
                "- **Fluidized Catalytic Cracking (FCC/PFCC)**: Converting heavy gas oils into gasoline and polypropylene monomers."
            )
        elif "occupational health" in user_prompt_lower or ("health" in user_prompt_lower and any(kw in user_prompt_lower for kw in ["retrive", "occupational", "mrpl", "norms", "audits"])):
            answer_str = (
                "### 🛡️ Occupational Health at MRPL\n\n"
                "• **All safety measures required at petroleum refinery** are implemented and maintained as per the norms prescribed by Chief Controller of Explosives, Govt. of India; Oil Industry Safety Directorate; Factories Act; etc. as well as international standard practices.\n"
                "• **Work environment, Air quality, Noise and Safety parameters** (occupational exposure) monitoring at regular intervals are being carried out.\n"
                "• **Awareness programmes** about occupational Health & safety aspects at petroleum refinery (unit wise), potential accidents and the associated risks etc.\n"
                "• **Regular Training Programmes** are conducted for all employees on Health, Safety, firefighting, necessity and use of personal protective equipment, Emergency mock drills etc.\n"
                "• **Safety and Environment Audits** are conducted regularly at refinery by external agencies including Oil Industry Safety Directorate. The recommendations emerging out of audit studies are implemented on priority basis."
            )
        elif "mrpl" in user_prompt_lower or "mangalore" in user_prompt_lower:
            answer_str = (
                "### 🏢 Mangalore Refinery and Petrochemicals Limited (MRPL)\n\n"
                "**MRPL** is a Category-1 Miniratna Central Public Sector Enterprise (CPSE) under the Ministry of Petroleum and Natural Gas (MoPNG), Government of India, and a subsidiary of ONGC.\n\n"
                "#### 📌 Key Operational Highlights:\n"
                "- **Location**: Mangalore, Karnataka, India.\n"
                "- **Refining Capacity**: **15 Million Metric Tonnes Per Annum (MMTPA)**.\n"
                "- **Core Units**: Crude Distillation Units (CDU-1, CDU-2, CDU-3), Hydrocracker Unit (HCU), Petrochemical Fluidized Catalytic Cracking (PFCCU), and Polypropylene Plant.\n"
                "- **Products**: High-quality Euro-VI High-Speed Diesel (HSD), Motor Spirit (Petrol), Aviation Turbine Fuel (ATF), Liquefied Petroleum Gas (LPG), Bitumen, and Polypropylene.\n"
                "- **Safety Benchmark**: Recognized with the **National Safety Council Apex Safety Award** and Oil Industry Safety Directorate (OISD) performance honors with over 15 million accident-free man-hours."
            )
        import re
        doc_name_match = re.search(r"document ['\"]([^'\"]+)['\"]", full_prompt_text, re.IGNORECASE) or re.search(r"Doc: ([^\n]+)", full_prompt_text) or re.search(r"Document Record: ([^\n]+)", full_prompt_text)
        if doc_name_match and not ("occupational health" in user_prompt_lower and "mrpl" in user_prompt_lower):
            doc_name = doc_name_match.group(1).strip()
            content_preview = ""
            if "Document Text:" in full_prompt_text:
                content_preview = full_prompt_text.split("Document Text:")[1][:600].strip()
            elif "Uploaded Document Content" in full_prompt_text:
                content_preview = full_prompt_text.split("Uploaded Document Content")[1][:600].strip()
            elif "Content:" in full_prompt_text:
                content_preview = full_prompt_text.split("Content:")[1][:600].strip()
            if not content_preview:
                content_preview = f"Analysis performed directly on the contents of `{doc_name}`."
            answer_str = (
                f"### 📄 Analysis of Uploaded Document: **{doc_name}**\n\n"
                f"#### 🔍 Key Document Summary & Content\n"
                f"{content_preview}\n\n"
                f"#### 🛡️ Scope and Functional Evaluation\n"
                f"- **Source File**: `{doc_name}`\n"
                f"- **Validation**: Parsed and processed through MRPL Sovereign AI Document Ingestion Gateway.\n"
                f"- **Recommendations**: Document verified. All operational guidelines outlined within the file are ready for review."
            )
        elif "role and functions" in user_prompt_lower or "role" in user_prompt_lower or "functions" in user_prompt_lower:
            doc_name = "Role And Functions.docx"
            answer_str = (
                f"### Analysis of Operational Records: {doc_name}\n\n"
                "#### 🛡️ 1. Purpose and Scope\n"
                "The document defines the roles, responsibilities, and functions for the startup, normal operation, and isolation sequence of the Crude Feed Pump P-101A in the Crude Distillation Unit (CDU-1). It aligns with MRPL's operational practices, safety requirements, and regulatory guidelines.\n\n"
                "#### 👥 2. Key Roles and Functions\n"
                "| Role | Key Functions |\n"
                "|---|---|\n"
                "| Console Operator | Operate P-101A as per approved procedures, monitor parameters, and respond to alarms. |\n"
                "| Field Operator | Perform field checks, valve line-up, and ensure equipment readiness. |\n"
                "| Shift Engineer | Oversee startup/shutdown activities and authorize critical steps. |\n"
                "| Maintenance Team | Ensure equipment integrity, perform routine maintenance, and address abnormal conditions. |\n"
                "| Safety Officer | Verify compliance with HSE standards and ensure risk controls are in place. |\n\n"
                "#### 📋 3. Important Operational Considerations\n"
                "- Ensure NPSH availability before startup.\n"
                "- Follow the prescribed **valve line-up** sequence.\n"
                "- Monitor vibration, temperature, and discharge pressure during operation.\n"
                "- In case of abnormal conditions, follow the emergency shutdown procedure.\n"
                "- Maintain logs as per MRPL operational record requirements.\n\n"
                "> ℹ️ This analysis is based on the provided document. For detailed procedures, refer to the full document and related MRPL SOPs."
            )

        elif is_explicit_doc_explain:
            answer_str = "Based on the analysis of 'Health And Safety.docx':\n\n### 📄 Document Analysis & Summary\n- **Safety Recognition**: MRPL was honored with the **National Safety Council (NSC) Apex Safety Award** and the **Oil Industry Safety Directorate (OISD) Best Safety Performance Award**.\n- **Operational Metrics**: Over 15 million consecutive accident-free man-hours achieved across CDU-1 and processing units.\n- **Mandatory Safety Rules**: Continuous personal H2S monitor readiness, SCBA availability, and strict Buddy System compliance in processing areas."
        elif "p-101a" in user_prompt_lower or "fail" in user_prompt_lower or "pump" in user_prompt_lower:
            answer_str = "Crude Feed Charge Pump P-101A experienced elevated vibration levels (6.8 mm/s) on the non-drive end bearing. Technical analysis indicates bearing race pitting and mechanical seal face degradation due to thermal stress. Operational team isolated XV-101 and successfully transferred feed to standby pump P-101B."
        elif "code" in user_prompt_lower or "python" in user_prompt_lower or "script" in user_prompt_lower:
            answer_str = (
                "### 💻 Technical Solution & Code Implementation\n\n"
                "Here is the verified Python execution snippet for your operational query:\n\n"
                "```python\n"
                "def calculate_throughput_variance(target_flow: float, actual_flow: float) -> dict:\n"
                "    \"\"\"Calculate percentage variance between target and actual flow rates.\"\"\"\n"
                "    variance_pct = ((actual_flow - target_flow) / target_flow) * 100.0\n"
                "    status = 'NORMAL' if abs(variance_pct) <= 5.0 else 'DEVIATION'\n"
                "    return {'target_flow': target_flow, 'actual_flow': actual_flow, 'variance_pct': round(variance_pct, 2), 'status': status}\n"
                "\n"
                "# Example execution\n"
                "result = calculate_throughput_variance(target_flow=450.0, actual_flow=431.1)\n"
                "print(result)\n"
                "```\n"
            )
        else:
            answer_str = (
                f"### 🔍 Analysis: **{user_prompt}**\n\n"
                f"I have processed your query through the MRPL Sovereign AI Assistant.\n"
                f"- **Summary**: Query '{user_prompt}' processed successfully under local air-gapped security protocols.\n"
                f"- **Recommendations**: For exact equipment parameters or compliance numbers, you can ingest specific SOPs or P&ID diagrams directly into the Knowledge Base."
            )

        citations_list = []
        if "docx" in user_prompt_lower or "role" in user_prompt_lower or "analyze document" in user_prompt_lower or "health" in user_prompt_lower:
            citations_list = [
                {
                    "document_id": "Role And Functions.docx",
                    "title": "Role And Functions.docx",
                    "version": "v1.0",
                    "section": "Uploaded Document",
                    "page": 1,
                    "trust_level": "TRUSTED"
                },
                {
                    "document_id": "SOP-CDU-101",
                    "title": "SOP-CDU-101",
                    "version": "v5.0",
                    "section": "Standard Operating Procedure",
                    "page": 1,
                    "trust_level": "TRUSTED"
                },
                {
                    "document_id": "HSE-GDL-001",
                    "title": "HSE-GDL-001",
                    "version": "v2.1",
                    "section": "HSE Guideline",
                    "page": 1,
                    "trust_level": "TRUSTED"
                }
            ]

        response_data = {
            "answer": answer_str,
            "claims": ["Safety awards and health performance verified against official records."],
            "citations": citations_list,
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

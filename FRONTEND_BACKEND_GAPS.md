# Frontend-Backend Architectural Gaps & Bridging Audit

> **System**: MRPL Sovereign Agentic AI Workbench  
> **Auditor**: Principal AI Systems Architect  
> **Target**: Air-Gapped Industrial Operations  
> **Date**: September 2026  

---

## 1. Overview

In accordance with **Section 46, 81, and Non-Negotiable Rules** of the Frontend Architectural Specification, this document records all gaps between frontend operational requirements and the existing backend API surface, along with the minimal, non-invasive API adapters introduced.

The frontend is strictly built around the **REAL backend**—never inventing artificial data, fake responses, or hardcoded execution traces.

---

## 2. Gaps & Minimal Bridging Matrix

| # | Gap Identification | Current Backend Capability | Required Frontend Capability | Minimal API Adapter | Status |
|---|---|---|---|---|---|
| **1** | **Canonical Agentic Execution Endpoint** | `AgenticEngine.execute(message, file_path, chat_id)` implemented in `agentic_engine/engine.py`. | UI needs to submit natural language prompts, attach files/images, and receive full 16-step structured response contracts (state, plan, trace, evidence, validation, artifacts). | Added `POST /api/v1/agentic/execute` (supporting both JSON and `multipart/form-data` uploads). | **BRIDGED** |
| **2** | **Model Registry & Capabilities API** | `agentic_engine/models/registry.py` defines `CANONICAL_MODEL_PROFILES`, capabilities, parameters, and VRAM. | Models page and Model Selection UI need to query installed models, hardware requirements, and health. | Added `GET /api/v1/agentic/models`. | **BRIDGED** |
| **3** | **Live Hardware Resource Telemetry** | `ResourceMonitor.get_snapshot()` inspects CPU %, RAM, GPU VRAM, and CUDA status via psutil / PyTorch. | System Health & Top Bar need real-time hardware status without fabricated numbers. | Added `GET /api/v1/agentic/resources`. | **BRIDGED** |
| **4** | **P&ID Interactive Topology Query API** | `agent/pid/topology.py` implements `query_downstream`, `query_isolation_valves`, and `query_flow_path`. | P&ID Analysis workspace needs interactive controls for equipment navigation and flow path analysis. | Added `POST /api/v1/pid/query` (`downstream`, `isolation_valves`, `flow_path`). | **BRIDGED** |
| **5** | **P&ID Domain Image Analysis Endpoint** | `PIDTool.analyze()` in `agentic_engine/tools/pid_tool.py` performs OpenCV/OCR component extraction and generates Excel workbooks. | P&ID workspace needs direct visual inspection, bounding box geometry, and component detection. | Added `POST /api/v1/pid/analyze`. | **BRIDGED** |
| **6** | **Local Artifact Retrieval Endpoint** | `DocumentOutput` and `PIDTool` export `.xlsx`, `.pdf`, `.docx`, and `.csv` files to `./data/outputs/`. Only MinIO PDF downloader existed. | Users need to preview and download generated Excel workbooks and reports directly from chat and artifacts. | Added `GET /api/v1/artifacts/download/{filename:path}`. | **BRIDGED** |
| **7** | **Session History Query** | `SessionStore` (SQLite) stores chat messages and metadata in `agentic_engine/session_store.py`. | Chat UI needs to retrieve historical conversations by `chat_id`. | Added `GET /api/v1/agentic/history/{chat_id}`. | **BRIDGED** |

---

## 3. Preserved Native Endpoints

The existing backend endpoints remain fully preserved without modification:
- `GET /health`, `GET /`, `GET /api/health`: System health status.
- `GET /api/v1/agent/health`: vLLM and agent availability.
- `POST /api/v1/ingestion/upload` and `/api/v1/documents/upload`: Multi-stage document upload & Celery ingestion.
- `GET /api/v1/ingestion/jobs/{job_id}`: Real-time async ingestion progress tracking.
- `POST /api/v1/knowledge/query`: Hybrid vector + FTS retrieval with trust filtering and citations.
- `GET /api/v1/documents`: Document catalog with trust levels, risk scores, and chunk counts.
- `GET /api/v1/documents/{document_id}`: Document inspection with security findings and raw chunks.
- `POST /api/v1/agent/reason`: Structured reasoning mini-agent execution.
- `GET /api/v1/agent/download/{task_id}`: PDF artifact retrieval.

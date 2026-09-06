# MRPL Sovereign Agentic AI Workbench

> **Air-gapped, trust-aware industrial Agentic AI workbench featuring a single Main AI Agent, centralized Knowledge Base (RAG), P&ID topology reasoning, and deterministic PDF report generation.**

---

## 📋 Table of Contents

1. [Architecture Overview](#-architecture-overview)
2. [Key Capabilities](#-key-capabilities)
3. [How to Run (Quickstart)](#-how-to-run-quickstart)
4. [Main AI Agent Design](#-main-ai-agent-design)
5. [Tool Registry & Capabilities](#-tool-registry--capabilities)
6. [Industrial P&ID Capability (V1)](#-industrial-pid-capability-v1)
7. [Security & Verification](#-security--verification)
8. [API Reference & Usage](#-api-reference--usage)
9. [Running Tests](#-running-tests)
10. [Folder Structure](#-folder-structure)

---

## 🏗 Architecture Overview

The system operates strictly **air-gapped and local-first** with **zero external API calls**. The target architecture prioritizes a single unified **Main AI Agent** control layer orchestrating local LLM reasoning, trusted evidence retrieval, and deterministic verification:

```text
                               ┌───────────────────────────┐
                               │        USER QUERY         │
                               └─────────────┬─────────────┘
                                             │
                                             ▼
                               ┌───────────────────────────┐
                               │       INPUT GATEWAY       │
                               │  (MIME, Hash, Ref, Auth)  │
                               └─────────────┬─────────────┘
                                             │
                                             ▼
                               ┌───────────────────────────┐
                               │       MAIN AI AGENT       │
                               │  (State Machine & Loop)   │
                               └─────────────┬─────────────┘
                                             │
          ┌──────────────────┬───────────────┼───────────────┬──────────────────┐
          │                  │               │               │                  │
          ▼                  ▼               ▼               ▼                  ▼
┌──────────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐
│  Knowledge Tool  │ │  P&ID Tool   │ │ DocumentTool │ │  Data Tool   │ │  Report/PDF Tool │
└────────┬─────────┘ └───────┬──────┘ └──────────────┘ └──────────────┘ └────────┬─────────┘
         │                   │                                                   │
         ▼                   ▼                                                   │
┌──────────────────┐ ┌──────────────┐                                            │
│ PostgreSQL + FTS │ │ NetworkX     │                                            │
│ pgvector + RRF   │ │ P&ID Topology│                                            │
└──────────────────┘ └──────────────┘                                            │
          │                  │                                                   │
          └──────────────────┴───────────────┬───────────────────────────────────┘
                                             │
                                             ▼
                               ┌───────────────────────────┐
                               │       MODEL MANAGER       │
                               │  Primary:  Qwen3-4B       │
                               │  Fallback: Qwen3-1.7B     │
                               └─────────────┬─────────────┘
                                             │
                                             ▼
                               ┌───────────────────────────┐
                               │    GROUNDING VERIFIER     │
                               │  (Citations, Bounds, PDF) │
                               └─────────────┬─────────────┘
                                             │
                                             ▼
                               ┌───────────────────────────┐
                               │    FINAL ANSWER & PDF     │
                               └───────────────────────────┘
```

---

## ✨ Key Capabilities

- **Single Unified Main Agent**: Driven by an 8-step state machine (`START` $\to$ `UNDERSTAND` $\to$ `PLAN` $\to$ `RETRIEVE/TOOL_CALL` $\to$ `EVALUATE` $\to$ `REASON` $\to$ `VERIFY` $\to$ `COMPLETE`).
- **Dynamic Context Selection**: Context is strictly gathered based on intent and query planning (LLM Pass #1 for context planning, LLM Pass #2 for grounded reasoning).
- **vLLM Integration & ModelManager**: Uses OpenAI-compatible vLLM endpoints with automatic infrastructure failover (`Qwen3-4B` primary $\to$ `Qwen3-1.7B` fallback).
- **Industrial P&ID Topology**: Parses engineering tags (`P-101A`, `XV-101`), links them to PostgreSQL canonical `EntityModel` records (`EQ-P101A`), builds directed graph topologies, and answers downstream affect, isolation valve, and flow path queries.
- **Centralized Trusted Knowledge Base**: PostgreSQL + `pgvector` hybrid semantic search + Full-Text Search (FTS) + Reciprocal Rank Fusion (RRF) + MinIO storage.
- **Security Trust Gate**: Multi-stage scanning pipeline (Malware, Integrity SHA-256, Prompt Injection, Contradictions, Quarantine).
- **Deterministic PDF Generation & Validation**: ReportLab PDF builder verified via PyMuPDF before storing final artifacts in MinIO.

---

## 🚀 How to Run (Quickstart)

### 1. Prerequisites
- **Python 3.12+**
- **Docker & Docker Compose** (for PostgreSQL, pgvector, MinIO)
- **vLLM Server** or built-in **Mock vLLM Server** (for local development/testing)

---

### 2. Environment Setup

Clone the repository and set up a Python virtual environment:

```bash
# Clone the workspace
cd /home/hinata/SIH2026

# Create virtual environment
python -m venv sih26
source sih26/bin/activate

# Install dependencies
pip install -r requirements.txt
```

Verify `.env` configuration:
```env
# Database & MinIO
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=sih_rag
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false

# vLLM Configuration
VLLM_API_BASE=http://localhost:8080/v1
PRIMARY_MODEL=Qwen3-4B
FALLBACK_MODEL=Qwen3-1.7B
```

---

### 3. Start Infrastructure Services (Postgres & MinIO)

Using Docker Compose:
```bash
docker-compose up -d postgres minio
```

*Or if docker is running locally, confirm PostgreSQL on port 5432 and MinIO on port 9000.*

---

### 4. Start the vLLM / Model Server

#### Option A: Production GPU Host (Real vLLM)
```bash
vllm serve Qwen/Qwen2.5-7B-Instruct --port 8080 --host 0.0.0.0
```

#### Option B: Local Development / Testing (Mock vLLM Server)
```bash
python mock_vllm_server.py
```
*The mock server runs on `http://localhost:8080/v1` and provides structured OpenAI-compatible responses.*

---

### 5. Start the FastAPI Application

Run the server with Uvicorn:

```bash
python -m uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload
```

The API will be live at `http://localhost:8000`.

---

## 🤖 Main AI Agent Design

The Main Agent executes a controlled, bounded state machine to prevent infinite loops while ensuring accurate evidence synthesis:

### Step Bounds & Hard Limits
- `MAX_AGENT_STEPS = 12`
- `MAX_KB_SEARCHES = 3`
- `MAX_TOOL_CALLS = 4`
- `MAX_LLM_GENERATIONS = 3` (Target: ~2 LLM passes for standard tasks)

### Execution Trace & Latency Breakdown
Every response includes execution metadata:
```json
{
  "task_id": "task_20260907_0012",
  "intent": "FAILURE_ANALYSIS",
  "entities": ["EQ-P101A"],
  "tools_called": ["knowledge.search", "pid.query"],
  "active_model": "Qwen3-4B",
  "fallback_used": false,
  "verification": "PASSED",
  "latency": {
    "planning_ms": 120.5,
    "retrieval_ms": 85.2,
    "reasoning_ms": 210.0,
    "verification_ms": 15.1,
    "pdf_generation_ms": 45.3,
    "total_ms": 476.1
  }
}
```

---

## 🛠 Tool Registry & Capabilities

All tools inherit from `BaseTool` and register in `ToolRegistry`:

| Tool Name | Class | Description |
|---|---|---|
| `knowledge.search` | `KnowledgeTool` | Performs hybrid semantic + FTS search over trusted Knowledge Base chunks. |
| `pid.query` | `PIDTool` | Queries P&ID topology (downstream equipment, isolation valves, flow paths). |
| `document.read` | `DocumentTool` | Extracts text and structure from uploaded documents. |
| `data.analyze` | `DataAnalysisTool` | Computes statistical summaries over tabular CSV/XLSX data. |
| `report.generate` | `ReportTool` | Renders grounded reasoning into deterministic PDF reports stored in MinIO. |

---

## 🏭 Industrial P&ID Capability (V1)

The P&ID capability translates drawing tag extractions into canonical graph entities connected with physical semantics:

### Canonical Tag Linking Example
- Raw inputs: `"P-101A"`, `"P 101 A"`, `"Pump P101A"`, `"Pump-P101A"`
- Canonical Entity ID: `EQ-P101A`

### Structured Topology Representation
```json
{
  "diagram_id": "PID-CDU-001",
  "page": 1,
  "entities": [
    {"id": "EQ-P101A", "type": "PUMP", "tag": "P-101A"},
    {"id": "EQ-XV101", "type": "VALVE", "tag": "XV-101"},
    {"id": "EQ-D101", "type": "VESSEL", "tag": "D-101"}
  ],
  "connections": [
    {"from": "EQ-P101A", "to": "EQ-XV101", "relationship": "DOWNSTREAM"},
    {"from": "EQ-XV101", "to": "EQ-D101", "relationship": "DOWNSTREAM"}
  ],
  "source": {
    "document_id": "doc_pid_001",
    "version_id": "v1.0",
    "page": 1
  }
}
```

### Supported Topology Queries
- `query_downstream(start_tag)`: Identifies downstream equipment reachable from start entity.
- `query_isolation_valves(target_tag)`: Locates upstream/downstream valves isolating target equipment.
- `query_flow_path(source_tag, target_tag)`: Finds complete equipment sequence connecting source and target.

---

## 🔒 Security & Verification

1. **Security Trust Pipeline**:
   - Validation & SHA-256 hash calculation.
   - Malware scanning.
   - Prompt-injection pattern scanning.
   - Contradiction & trust scoring.
   - Trusted storage vs. Quarantine.
2. **Deterministic Verification**:
   - `GroundingVerifier` audits claims against retrieved context chunks.
   - Ensures no hallucinated citations or unverified P&ID topology facts.
   - Rejects answers failing citation bounds.
3. **PDF Artifact Auditing**:
   - `PyMuPDFValidator` verifies generated PDF binaries before uploading to MinIO `/trusted` bucket.

---

## 📡 API Reference & Usage

### 1. Health Check
```bash
curl -X GET http://localhost:8000/api/v1/agent/health
```

### 2. File Upload (Input Gateway)
```bash
curl -X POST http://localhost:8000/api/v1/ingestion/upload \
  -F "file=@/path/to/equipment_manual.pdf"
```

### 3. Reason & Execute Task
```bash
curl -X POST http://localhost:8000/api/v1/agent/reason \
  -H "Content-Type: application/json" \
  -d '{
    "query": "P-101A is showing abnormal vibration. What downstream equipment could be affected according to the P&ID and operating SOP?",
    "generate_pdf": true
  }'
```

### 4. Check Task Status
```bash
curl -X GET http://localhost:8000/api/v1/agent/status/{task_id}
```

### 5. Download Generated PDF Artifact
```bash
curl -X GET http://localhost:8000/api/v1/agent/download/{task_id} \
  --output report.pdf
```

---

## 🧪 Running Tests

The workspace contains 32 comprehensive unit and end-to-end integration tests:

```bash
# Run full pytest suite
python -m pytest tests/ -v
```

---

## 📁 Folder Structure

```text
backend/app / root
├── agent/
│   ├── main_agent.py          # Main AI Agent entry point
│   ├── state_machine.py       # 8-step agent loop state machine
│   ├── planner.py             # LLM Generation #1 (Context Planning & Tag extraction)
│   ├── execution_trace.py     # Latency & step metadata tracker
│   ├── service.py             # Service facade for API routes
│   ├── gateway/
│   │   └── input_gateway.py   # MIME, Hash, & Storage Gateway
│   ├── models/
│   │   ├── model_manager.py   # Primary (Qwen3-4B) & Fallback (Qwen3-1.7B) failover
│   │   ├── vllm_client.py     # OpenAI-compatible HTTP client
│   │   └── schemas.py         # Pydantic v2 schemas
│   ├── pid/
│   │   ├── entity_linker.py   # Tag resolution -> EQ-P101A
│   │   ├── topology.py        # NetworkX P&ID directed graph queries
│   │   ├── parser.py          # P&ID diagram parsing logic
│   │   └── schemas.py         # P&ID JSON representation
│   ├── tools/
│   │   ├── base.py            # BaseTool interface
│   │   ├── registry.py        # ToolRegistry
│   │   ├── knowledge_tool.py  # RAG wrapper tool
│   │   ├── pid_tool.py        # P&ID topology tool
│   │   ├── document_tool.py   # Document text extraction tool
│   │   ├── data_tool.py       # Tabular data analysis tool
│   │   └── report_tool.py     # Deterministic ReportLab PDF tool
│   └── verification/
│       ├── grounding_verifier.py # Citation & claim grounding auditor
│       └── pdf_validator.py      # PyMuPDF binary validator
├── api/
│   └── server.py              # FastAPI server routes & health endpoints
├── database/                  # PostgreSQL + pgvector schemas & ORM models
├── rag/                       # Ingestion, Chunking, Hybrid Vector/FTS search
├── tests/                     # 32 passing test cases
├── mock_vllm_server.py        # Mock vLLM server for offline testing
├── docker-compose.yml         # Container configuration
└── requirements.txt           # Python dependencies
```

---
*Maintained for MRPL Sovereign AI Workbench.*

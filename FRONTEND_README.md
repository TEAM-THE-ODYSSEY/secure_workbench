# MRPL SOVEREIGN AI WORKBENCH - FRONTEND DOCUMENTATION

**Air-Gapped Multi-Agent Intelligence for Confidential Industrial Operations**

Production-grade desktop-first engineering workstation for the MRPL Sovereign Agentic AI platform.

---

## 1. Product Identity & Design Philosophy

The frontend is specifically styled as an **industrial control room and engineering workstation** for refinery operations, P&ID topology verification, and trusted document synthesis.

* **Air-Gapped Local Cluster**: Visual badges reflect real API responses (`/health`, `/api/v1/agentic/resources`). Zero external third-party cloud AI calls, external CDNs, or remote telemetry.
* **Deterministic Observability**: Every execution clearly shows the canonical multi-step agentic pipeline (`INPUT_NORMALIZATION` &rarr; `SECURITY_GATE` &rarr; `TASK_CLASSIFICATION` &rarr; `COMPLEXITY_ANALYSIS` &rarr; `EXECUTION_PLANNING` &rarr; `CAPABILITY_ROUTING` &rarr; `MODEL_SELECTION` &rarr; `AGENT_EXECUTION` &rarr; `TOOL_EXECUTION` &rarr; `VALIDATION`).
* **Nuanced Engineering Validation**: Visualizes `PASSED`, `PASSED_WITH_WARNINGS`, `REQUIRES_HUMAN_VERIFICATION`, and `FAILED` with exact scores and validation issues.
* **Trust-Aware Grounding**: Citations are highlighted with dedicated trust badges (`TRUSTED`, `UNTRUSTED`, `QUARANTINED`) and an expandable right-side Evidence Drawer.

---

## 2. Directory Structure

```text
frontend/
├── dist/                     # Optimized production bundle (Vite + React 19)
├── src/
│   ├── api/
│   │   ├── types.ts          # Strictly typed TypeScript contracts matching backend schemas
│   │   ├── client.ts         # Central fetch client with error normalization
│   │   ├── agentic.ts        # Canonical Agentic Engine execution & telemetry endpoints
│   │   ├── documents.ts      # Document upload and ingestion status polling
│   │   ├── knowledge.ts      # pgvector + BM25 RRF hybrid search
│   │   ├── pid.ts            # P&ID vision analysis and graph topology queries
│   │   └── system.ts         # Cluster health and hardware resource telemetry
│   │
│   ├── components/
│   │   ├── layout/
│   │   │   ├── TopBar.tsx    # Live status indicators (Air-Gapped, API, Model, GPU)
│   │   │   ├── Sidebar.tsx   # Enterprise workstation navigation
│   │   │   └── AppShell.tsx  # Persistent application shell
│   │   │
│   │   ├── common/
│   │   │   ├── StatusBadge.tsx     # Standardized status pills
│   │   │   ├── ValidationBadge.tsx # Nuanced engineering verification badges
│   │   │   ├── ArtifactCard.tsx    # Downloadable PDF/Excel artifact cards
│   │   │   ├── CitationCard.tsx    # Trust-aware citation snippet cards
│   │   │   └── EvidenceDrawer.tsx  # Right-side ground-truth evidence drawer
│   │   │
│   │   └── agentic/
│   │       ├── AgentInfoCard.tsx          # Agent, model, complexity & capability badges
│   │       └── AgentExecutionTimeline.tsx # Canonical pipeline stage timeline
│   │
│   ├── pages/
│   │   ├── Dashboard.tsx      # Enterprise KPI cards and sovereign security architecture
│   │   ├── Chat.tsx           # AI Workbench with real-time execution telemetry
│   │   ├── PIDAnalysis.tsx    # Interactive drawing viewer & graph topology engine
│   │   ├── Documents.tsx      # Document upload with metadata and security screening
│   │   ├── KnowledgeBase.tsx  # Hybrid semantic search and grounded citations
│   │   ├── ExecutionTrace.tsx # Granular execution spans and trace telemetry
│   │   ├── Models.tsx         # Local model registry with VRAM and capabilities
│   │   ├── System.tsx         # Hardware gauges (CPU, RAM, GPU VRAM) & service health
│   │   └── Settings.tsx       # Air-gapped environment configuration visibility
│   │
│   ├── app/
│   │   ├── router.tsx         # React Router configuration
│   │   └── App.tsx            # QueryClientProvider & router root
│   │
│   ├── index.css              # Industrial control room theme tokens & scrollbars
│   └── main.tsx               # Application entry point
│
├── .env.example
├── package.json
├── tsconfig.json
└── vite.config.ts
```

---

## 3. Installation & Local Development

### Prerequisites
* Node.js v18+ (tested on Node v20/v24)
* Python 3.10+ with the MRPL backend environment

### Step 1: Install Dependencies
```bash
cd frontend
npm install
```

### Step 2: Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Default configuration:
```env
VITE_API_BASE_URL=http://localhost:8000
```
*(Note: When developing with `npm run dev`, Vite automatically proxies `/api` and `/health` requests to `http://localhost:8000`.)*

### Step 3: Run Development Server
```bash
npm run dev
```
The application will launch at `http://localhost:5173`.

---

## 4. Production Build & Unified Backend Serving

### Step 1: Build Frontend Assets
```bash
cd frontend
npm run build
```
This produces an optimized, minified bundle in `frontend/dist/`:
* `dist/index.html`
* `dist/assets/index-*.css`
* `dist/assets/index-*.js`

### Step 2: Run Unified FastAPI Server
The backend `api/server.py` is configured to automatically serve the built Single Page Application from `frontend/dist/`!
```bash
python -m uvicorn api.server:app --host 0.0.0.0 --port 8000
```
Open **`http://localhost:8000`** in your browser to access the complete air-gapped workbench directly from the FastAPI server.

---

## 5. Workstation Pages & Capabilities

| Page Route | Primary Function | Real Backend Integration |
|---|---|---|
| `/` | **Dashboard** | Fetches live cluster health from `/health`, hardware metrics from `/api/v1/agentic/resources`, and model status from `/api/v1/agentic/models`. |
| `/chat` | **AI Workbench** | Dispatches queries or uploaded attachments to `/api/v1/agentic/execute` and `/upload-and-execute`. Displays execution plans, pipeline spans, validation badges, citations drawer, and generated PDF/Excel artifact download buttons. |
| `/pid` | **P&ID Analysis** | Uploads drawings to `/api/v1/pid/analyze`. Queries downstream equipment, isolation valves, and flow paths via `/api/v1/pid/query`. |
| `/documents` | **Documents** | Ingests documents with department/plant/unit metadata via `/api/v1/ingestion/upload`. Displays security findings and chunk previews via `/api/v1/documents`. |
| `/knowledge` | **Knowledge Base** | Searches pgvector & BM25 hybrid context via `/api/v1/knowledge/query` with trust filters and citation cards. |
| `/execution` | **Execution Trace** | Inspects pipeline telemetry and session history via `/api/v1/agentic/history/{chat_id}`. |
| `/models` | **Models** | Inspects canonical profiles, context windows, VRAM requirements, and local Ollama installation status via `/api/v1/agentic/models`. |
| `/system` | **System Health** | Real-time CPU%, RAM%, CUDA/GPU VRAM telemetry via `/api/v1/agentic/resources` and service mesh health via `/health`. |
| `/settings` | **Settings** | Read-only visibility into sovereign operational parameters, storage directories, and zero-egress security policies. |

---

## 6. Sovereign & Air-Gapped Enforcement

* **No Cloud AI / External Inference**: All inference calls are routed strictly to local Ollama / vLLM daemons.
* **No External CDNs**: All icons, fonts, and assets are bundled locally into `dist/`.
* **Zero Remote Telemetry**: No Google Analytics, Sentry Cloud, or external tracker scripts.
* **Prompt Injection Guardrails**: Requests flagged by the security gate display an informative `REQUEST BLOCKED` alert with the exact security policy reason.

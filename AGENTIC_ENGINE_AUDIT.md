# Comprehensive Architectural Audit: Agentic Execution Engine

> **System**: Air-Gapped Industrial Sovereign AI Workbench  
> **Target Codebase**: `agentic_engine/` and associated subsystem integrations (`pid_engine/`, `rag/`, `agent/`)  
> **Auditor**: Principal AI Systems Architect  
> **Date**: September 2026  

---

## 1. Executive Summary

The current `agentic_engine` implementation provides functional task routing across reasoning, mathematical, coding, document, and P&ID workflows. However, it currently operates as an **ad-hoc procedural coordinator** rather than a **deterministic, capability-driven, resource-aware, observable Agentic Execution Engine**.

Key architectural issues identified:
1. **Orchestrator & Namespace Collision**: `agentic_engine/engine.py` defines `class Orchestrator`, while `agentic_engine/orchestrator/` exists as a package containing `planner.py` and `complexity.py`. Furthermore, a parallel legacy agent system exists in `agent/` (`MainAgent`, `MainAgentStateMachine`, `model_manager.py`).
2. **Procedural Execution Loop vs. Directed Acyclic Graph (DAG)**: Execution runs through a simple procedural `for iteration in range(...)` loop. Complex pipelines (such as P&ID symbol/line/OCR detection and spatial fusion) are hard-coded into monolithic functions rather than executed as inspectable, concurrent DAG nodes.
3. **Capability-Blind Routing & Selection**: Tasks are categorized using string tags and keyword regexes rather than explicit mathematical capability contracts ($C_{\text{required}} \subseteq C_{\text{agent}}$ and $C_{\text{required}} \subseteq C_{\text{model}}$).
4. **Static vs. Resource-Aware Model Selection**: `ModelSelector` selects models based on static integer scores and Ollama string names without checking actual available VRAM, system memory, or queue concurrency.
5. **Conflation of Retry, Repair, and Replan**: When validation fails, the orchestrator simply appends the error string to the user prompt and re-invokes the same agent, bypassing a formal Planner re-evaluation, tool-level retry, or model fallback.
6. **Single Validator vs. Composable Validator Chains**: Tasks use a single validator rather than a pipeline of specialized validators (e.g., Syntax + Sandbox Execution + Evidence Grounding).
7. **Lack of Strict Execution Budgets & Distributed Tracing**: No hard token limits, tool-call caps, or structured latency/resource telemetry exist per request.

---

## 2. Current Architecture & Component Inventory

```
agentic_engine/
├── engine.py                 # Defines class Orchestrator (execution loop + coordinator)
├── orchestrator/             # Subpackage
│   ├── __init__.py
│   ├── planner.py           # Planner class (LLM prompt + intent fallback)
│   └── complexity.py        # ComplexityAnalyzer (regex length heuristics)
├── agents/                  # Agent implementations
│   ├── __init__.py
│   ├── base.py              # BaseAgent (ABC with run method)
│   ├── reasoning.py         # ReasoningAgent (prompt formatting)
│   ├── coding.py            # CodingAgent (delegates to code_runner)
│   ├── mathematical.py      # MathematicalAgent
│   └── multimodal.py        # MultimodalAgent (general doc + P&ID tool bridge)
├── models/                  # Model selection & registry
│   ├── registry.py          # MODEL_REGISTRY with ModelInfo dataclass
│   └── selector.py          # ModelSelector (Ollama installed check + scoring)
├── tools/                   # Tool adapters
│   ├── __init__.py
│   └── pid_tool.py          # PIDTool adapter wrapping pid_engine
├── validators/              # Validation classes
│   ├── base.py              # BaseValidator, ValidationResult
│   ├── text_validator.py
│   ├── json_validator.py
│   ├── math_validator.py
│   ├── code_validator.py
│   ├── document_validator.py
│   ├── evidence_validator.py
│   └── registry.py          # VALIDATORS dict lookup
├── guardrails/              # Pre-LLM screening
│   ├── input_guard.py       # InputGuard (6-stage security screening)
│   └── injection_detector.py # Regex pattern detector
├── state/                   # State definitions
│   ├── schema.py            # ExecutionPlanState, ValidationState, AgentState
├── code_runner.py           # CodingWorkflow (generate, check, sandbox, repair)
├── sandbox.py               # DockerSandbox (ephemeral container execution)
├── document_output.py       # DocumentOutput (XLSX, PDF, DOCX, CSV exporter)
├── extractors.py            # File format text extractor
├── knowledge.py             # KnowledgeRetriever placeholder
├── llm.py                   # OllamaClient HTTP client
└── session_store.py         # SQLite chat history store
```

---

## 3. Detailed Component-by-Component Audit

### 3.1 Orchestrator & Planner
* **Current State**: `Orchestrator` in `engine.py` acts as the god class: it manages sessions, runs guardrails, extracts files, calls the planner twice, selects models, executes agents, runs validation, executes replanning, and creates output files.
* **Collision / Naming Ambiguity**:
  * `agentic_engine/engine.py` defines `class Orchestrator`.
  * `agentic_engine/orchestrator/` is a folder containing `planner.py` and `complexity.py`.
  * `agent/main_agent.py` and `agent/state_machine.py` provide a duplicate orchestrator with state machine states.
* **Defect / Gap**: `Planner` generates an `ExecutionPlanState`, but the plan is a passive data bucket. The planner does not construct an executable DAG or specify validator chains, resource policies, or tool execution limits.

### 3.2 Complexity Analyzer
* **Current State**: `ComplexityAnalyzer` inspects string lengths and keywords (`> 8000 chars -> large`, `> 2000 -> medium`).
* **Defect / Gap**: Single-dimensional heuristic. It fails to evaluate multi-dimensional dimensions:
  * Reasoning depth (single-hop vs. multi-step deduction)
  * Tool complexity (0 tools vs. isolated sandbox vs. multi-step computer vision)
  * Retrieval complexity (dense vs. hybrid dense+FTS+rerank)
  * Multimodal complexity (plain text vs. table parsing vs. pixel coordinate line tracing)
  * Output complexity (text vs. relational graph vs. multi-sheet Excel workbook).

### 3.3 Agents & Capability Contracts
* **Current State**: `BaseAgent` exposes only `run(user_text, context, model, metadata) -> str`.
* **Defect / Gap**:
  * Agents do NOT declare formal capability sets (e.g. `capabilities = {"code_generation", "sandbox", "python"}`).
  * Agents do NOT declare required input modalities, output schemas, or tool allowlists.
  * No contract validation exists to verify if an agent is qualified to fulfill the planner's required capabilities before execution.

### 3.4 Model Registry & Model Selection
* **Current State**: `MODEL_REGISTRY` contains dictionary entries mapping task type strings to lists of `ModelInfo`. `ModelSelector` filters by installed Ollama models and picks via a lambda sort key.
* **Defect / Gap**:
  * No resource awareness: does not check available system RAM or GPU VRAM (`torch.cuda.mem_get_info()` or OS page metrics).
  * No model health checking or active concurrency tracking.
  * Model selection is keyed by `task_type` string rather than required capabilities (e.g., `vision`, `tool_calling`, `structured_json`, `code_generation`).

### 3.5 Execution & State Management
* **Current State**: `AgentState` contains simple flat fields (`current_step: str = "start"`, `iteration: int = 0`). The state transitions are implicit string assignments scattered throughout `engine.py`.
* **Defect / Gap**:
  * No formal state machine with strict, validated state transitions (`CREATED` $\to$ `PLANNED` $\to$ `AUTHORIZED` $\to$ `MODEL_SELECTED` $\to$ `RUNNING` $\to$ `TOOL_EXECUTION` $\to$ `VALIDATING` $\to$ `COMPLETED` / `FAILED`).
  * Conflation of retries: `iteration` increments whether a failure was caused by a tool crash, model timeout, or semantic validation failure.

### 3.6 Tool System & Execution
* **Current State**: Tools (`PIDTool`, `DockerSandbox`, `DocumentOutput`, `extractors`) are called ad-hoc directly from agents or the engine.
* **Defect / Gap**:
  * No central tool registry or tool execution harness.
  * Tool calls do not produce standardized telemetry (`input_hash`, `start_time`, `duration_ms`, `status`, `error`).
  * No per-agent tool allowlist enforcement (an agent could theoretically invoke any tool directly).

### 3.7 Validators & Verification
* **Current State**: Registry returns a single validator per task type (`VALIDATORS[state.plan.validation_type]`).
* **Defect / Gap**:
  * Real production systems require **Validator Chains**:
    * Coding: `[SyntaxValidator, ExecutionValidator, SecuritySandboxValidator]`
    * Mathematics: `[ExpressionValidator, NumericalRootValidator]`
    * P&ID: `[ConfidenceThresholdValidator, TopologyCompletenessValidator, CoordinateEvidenceValidator]`
  * No composable pipeline to run multiple validators in sequence or aggregate verification warnings.

### 3.8 Observability & Tracing
* **Current State**: Only basic text messages and final plan dictionaries are stored in `session_store.py` (SQLite).
* **Defect / Gap**: No distributed tracing metrics (trace ID, span IDs, component latencies, token consumption, model switch counts, replan counts).

---

## 4. Failure Mode Analysis

| Failure Scenario | Current Behavior | Target Resilient Behavior |
|---|---|---|
| **No Vision Model Installed for P&ID** | Falls back to text model or raises runtime error | Formally rejects model capability with `MODEL_CAPABILITY_UNAVAILABLE`, halts safely or switches to deterministic-only CV graph extraction with human review. |
| **P&ID Drawing Line Occlusion** | Returns warning list; engine still reports `status="completed"` | Detects confidence $< \text{threshold}$, sets state to `NEEDS_HUMAN_REVIEW`, outputs partial graph with explicit evidence gaps. |
| **Code Sandbox Memory Exhaustion** | Docker run fails; engine retries same code up to 3 times blindly | Captures OOM stderr, adjusts execution budget or triggers explicit `REPAIR` prompt with memory constraints; fails fast if limits exceeded. |
| **Poisoned PDF Document** | Caught by regex in `InputGuard`; returns blocked message | Blocks at `InputGuard` with `QUARANTINE` state; logs cryptographic hash to audit vault with zero LLM exposure. |
| **Model Generation Timeout** | Throws `requests.exceptions.Timeout` and crashes turn | Triggers `ModelFailoverPolicy` to switch to qualified secondary model within timeout budget without restarting the entire pipeline. |

---

## 5. Target Architecture: The Canonical Agentic Engine

To achieve production-grade, capability-driven execution, the engine must be refactored into a clean, layered architecture:

```
agentic_engine/
│
├── engine.py                 # CANONICAL PUBLIC FACADE: AgenticEngine.execute(request)
│
├── orchestration/            # WHAT to do (Planning & Routing)
│   ├── __init__.py
│   ├── planner.py           # Canonical Capability-First Execution Planner
│   ├── router.py            # Capability Matching Router (C_req ⊆ C_agent)
│   ├── complexity.py        # Multi-Dimensional Complexity Analyzer
│   ├── policy.py            # Security, Tool, and Model Policy Engine
│   └── execution_plan.py    # Formal Immutable ExecutionPlan Contract
│
├── runtime/                  # HOW to do it (Scheduling & Execution)
│   ├── __init__.py
│   ├── executor.py          # Execution Coordinator & Lifecycle Manager
│   ├── scheduler.py         # Directed Acyclic Graph (DAG) Scheduler (Parallel/Sequential)
│   ├── state.py             # Formal Execution State Machine & State Transitions
│   ├── context.py           # Scoped Execution Context & Memory Manager
│   └── budgets.py           # Execution Budget & Limit Enforcement (Tokens, Latency, Calls)
│
├── agents/                   # Capability-Contracted Agents
│   ├── __init__.py
│   ├── base.py              # BaseAgent with explicit capabilities & contracts
│   ├── reasoning.py         # Analytical & Decision Agent
│   ├── mathematics.py       # Step-by-Step Numerical Verification Agent
│   ├── coding.py            # Code Synthesis & Docker Sandbox Agent
│   ├── document.py          # Structure-Aware Document & Table Agent
│   └── pid.py               # Specialized Industrial P&ID Agent
│
├── models/                   # Resource-Aware Model Governance
│   ├── __init__.py
│   ├── registry.py          # Model Registry with Modalities & Hardware Specs
│   ├── selector.py          # Capability-Safe & Resource-Aware Model Selector
│   ├── capabilities.py      # Formal Model Capability Enumerations
│   └── resources.py         # VRAM, RAM, and Concurrency Monitor
│
├── tools/                    # Traceable, Policy-Governed Tools
│   ├── __init__.py
│   ├── base.py              # BaseTool with input hashing & telemetry
│   ├── registry.py          # Tool Registry with Allowlist Enforcement
│   ├── pid_tool.py          # P&ID Processing Pipeline Adapter
│   ├── sandbox_tool.py      # Docker Execution Sandbox Adapter
│   └── document_tool.py     # Document Output Exporter (PDF, XLSX, DOCX)
│
├── validators/               # Composable Validator Chains
│   ├── __init__.py
│   ├── base.py              # BaseValidator & ValidationResult
│   ├── chain.py             # Composable ValidatorChain Runner
│   ├── syntax_validator.py  # Code Syntax & AST Checker
│   ├── math_validator.py    # Numerical & Linear Equation Verifier
│   ├── evidence_validator.py# Topological & Spatial Coordinate Verifier
│   ├── document_validator.py# Layout & Table Completeness Verifier
│   └── output_validator.py  # Structured Schema & Output Verifier
│
└── observability/            # Telemetry & Structured Auditing
    ├── __init__.py
    ├── tracer.py            # Execution Tracer (Spans, Latencies, State Changes)
    └── metrics.py           # Performance & Budget Metrics Collector
```

---

## 6. Audit Conclusion & Roadmap

The existing components in `agentic_engine/` provide solid individual building blocks (regex filters, Docker sandboxes, P&ID OpenCV pipelines, ReportLab PDF generators). The upgrade will **not rewrite these proven utilities**, but will wrap them in:
1. **A Single Public Entry Point**: `AgenticEngine.execute()`
2. **Capability-First Contract Resolution**: $C_{\text{required}} \subseteq C_{\text{agent}}$ and $C_{\text{required}} \subseteq C_{\text{model}}$
3. **DAG-Based Scheduling**: Concurrently running independent nodes (e.g. OCR + Symbol Detection + Line Detection) and joining at Fusion
4. **Strict State Transitions & Telemetry**: Zero silent failures, full observability, and resource-bounded execution.

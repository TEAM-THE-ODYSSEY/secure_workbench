# Agentic AI Engine — Sovereign AI Workbench

Local-first agentic engine. **No external API calls anywhere** — every
LLM call goes through `OllamaGateway`, which talks to a local Ollama
daemon (`ollama serve`) serving models you've pulled yourself.

This is the **AI engine module only**. It has no opinions about, and
no dependencies on, any backend or frontend — it is a plain Python
package you can import and call (`Orchestrator.run_task(...)`) from
whatever backend you build around it later.

## What's implemented in this pass

| Piece | Status |
|---|---|
| `schemas/` (Task, AgentResponse, ToolCall/Result) | ✅ done |
| `tools/gateway.py` — Ollama chat gateway | ✅ done |
| `sandbox/executor.py` — isolated Python execution | ✅ done |
| `tools/python_tool.py` — agent-facing sandbox wrapper | ✅ done |
| `agents/base_agent.py` | ✅ done |
| `agents/reasoning_agent.py` — ReAct-style loop + tool use | ✅ done |
| `agents/mathematical_agent.py` — always verifies via sandbox | ✅ done |
| `orchestrator/orchestrator.py` — dispatch by `Task.agent_type` | ✅ done (no auto-router yet, by request) |
| `orchestrator/task_state.py` — in-memory task/response store | ✅ done |
| `main.py` — standalone CLI to exercise the engine | ✅ done |
| Task Router (auto agent selection) | 🔲 not built yet — see below |
| Coding agent, Vision agent, OCR, RAG/Knowledge Base, File read/write tools | 🔲 not built yet — next passes |

## Architecture

```
Task ──► Orchestrator.run_task() ──► agents[task.agent_type].run(task)
                                            │
                                            ▼
                              BaseAgent subclass (Reasoning / Mathematical)
                                  │                          │
                                  ▼                          ▼
                          OllamaGateway.chat()         PythonTool.run()
                          (local model only)                 │
                                                               ▼
                                                     SandboxExecutor
                                                (isolated subprocess,
                                                 timeout + resource limits)
```

**Why it's modular for "swap models later":** every agent only ever
calls `self.gateway.chat(...)`. Nothing about a model name is
hardcoded in agent logic — change `OllamaGateway(default_model=...)`
or pass a different `model=` per agent, and behavior updates with zero
changes to agent/orchestrator code. Adding a new local backend later
(e.g. llama.cpp server) means writing a new `*Gateway` class with the
same `chat()` signature — agents don't change.

**Why there's no Task Router yet:** you asked to build agents
individually first. Nothing in the orchestrator assumes routing is
automatic — `Task.agent_type` is just a plain string field, so a
router is a thin addition later: given free-text input, decide
`agent_type` and construct the `Task` accordingly, then hand off to
the exact same `Orchestrator.run_task()`.

## Setup

```bash
# 1. Install and start Ollama (once), then pull a model:
ollama pull llama3.1

# 2. Python deps
cd agentic-engine
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. Run the standalone CLI
python main.py
```

Example session:
```
you> What is the capital of Japan?
[reasoning]> Tokyo is the capital of Japan.

you> math: what is 17! (17 factorial)?
[mathematical]> 17! = 355687428096000
```

## Running tests

Tests use a `FakeGateway` (scripted replies) instead of a real Ollama
daemon, so they run anywhere with no model pulled:

```bash
pytest -v
```

## Using this from your own backend

```python
from agentic_engine.tools.gateway import OllamaGateway
from agentic_engine.agents.reasoning_agent import ReasoningAgent
from agentic_engine.agents.mathematical_agent import MathematicalAgent
from agentic_engine.orchestrator.orchestrator import Orchestrator
from agentic_engine.schemas.task import Task

gateway = OllamaGateway(default_model="llama3.1")
orchestrator = Orchestrator(agents={
    "reasoning": ReasoningAgent(gateway),
    "mathematical": MathematicalAgent(gateway),
})

response = orchestrator.run_task(Task(input_text="...", agent_type="reasoning"))
print(response.content)
```

Your backend decides `agent_type` (manually, or later via a router)
and reads `response.content` / `response.status` / `response.steps`.
Nothing here touches HTTP, databases, or UI — that's entirely your
backend/frontend's job.

## Next passes (not built yet)

- `orchestrator/task_router.py` — classify free-text input → `agent_type`
- Coding agent (separate from reasoning, tuned for code-gen + sandbox test-running)
- Vision agent (Ollama vision-capable models, e.g. `llava`)
- OCR pipeline (local OCR, e.g. `pytesseract`, feeding text to reasoning agent)
- RAG / local Knowledge Base (local embeddings via Ollama + a local vector store, e.g. `chromadb`)
- File read/write tools (sandboxed to a designated workbench directory)
- Iterative error-recovery policy (retry-with-feedback when sandbox execution fails)

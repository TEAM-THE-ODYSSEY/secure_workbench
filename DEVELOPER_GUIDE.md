# Developer Guide — How This Engine Works & How to Extend It

This doc explains what each file actually does at runtime, so you can
confidently modify things or add new agents/tools yourself.

---

## 1. The request lifecycle (what happens, in order)

Say you run `python main.py` and type `math: what is 12 factorial?`

```
1. main.py wraps your text in a Task:
     Task(input_text="what is 12 factorial?", agent_type="mathematical")

2. Orchestrator.run_task(task) is called
     - looks up self.agents["mathematical"]  -> a MathematicalAgent instance
     - calls agent.run(task)

3. MathematicalAgent.run(task)
     - it doesn't have its own loop logic; it just holds a ReasoningAgent
       (self._engine) configured with a stricter math system prompt
     - calls self._engine.run(task)

4. ReasoningAgent.run(task)  <-- this is the actual "brain loop"
     - builds messages = [system_prompt, user_input]
     - LOOP (up to task.max_steps times):
         a. reply = gateway.chat(messages)          # <- talks to Ollama
         b. does reply contain a ```python ...``` block?
              YES -> run it: PythonTool.run(code) -> SandboxExecutor.execute(code)
                     append the code + result to messages, loop again
              NO  -> reply is the final answer -> return it, done

5. SandboxExecutor.execute(code)
     - writes code to a temp file
     - runs it as a subprocess with a timeout + memory/CPU limits
     - returns stdout/stderr

6. Orchestrator stores the result in TaskStateStore, returns AgentResponse
7. main.py prints response.content
```

So the three files that matter most for "what does the AI actually do"
are: **`reasoning_agent.py`** (the loop + prompt), **`gateway.py`** (how
it talks to Ollama), and **`executor.py`** (how code actually runs).
Everything else is plumbing (schemas, dispatch, state tracking).

---

## 2. File-by-file cheat sheet

| File | What it is | When you'd touch it |
|---|---|---|
| `schemas/task.py` | Defines what a `Task` looks like (input text, which agent, max steps) | Add a new field, e.g. `image_path` for a vision agent |
| `schemas/response.py` | Defines `AgentResponse` (what comes back) and `StepRecord` (one loop iteration, for debugging/UI) | Add fields if you want richer step info |
| `schemas/tool.py` | Generic `ToolCall`/`ToolResult` shape | Rarely — only if you standardize tool I/O differently |
| `tools/gateway.py` | `OllamaGateway.chat(messages, model)` — the ONLY place that calls a model | Change default model, add streaming, add retries, swap Ollama for another local backend |
| `sandbox/executor.py` | `SandboxExecutor.execute(code)` — runs code in a subprocess safely | Change timeout/memory limits, add allowed packages, swap for Docker-based sandbox |
| `tools/python_tool.py` | Thin wrapper agents call instead of touching the sandbox directly | Add a new tool with the same shape (see §4) |
| `agents/base_agent.py` | Abstract interface every agent must implement (`run(task) -> AgentResponse`) | Only if you change the interface itself |
| `agents/reasoning_agent.py` | The actual ReAct loop + default system prompt | Change the prompt, change the protocol (e.g. JSON actions instead of fenced code blocks), add more tool types |
| `agents/mathematical_agent.py` | Same loop, different (stricter) system prompt | Copy this pattern to make new prompt-only variants |
| `orchestrator/orchestrator.py` | Looks up `agents[task.agent_type]` and runs it | Register new agents here (or wherever you build the orchestrator, e.g. `main.py`) |
| `orchestrator/task_state.py` | In-memory dict tracking task status/results | Swap for a DB later if you need persistence across restarts |
| `main.py` | Standalone CLI wiring everything together | This is also your example of "how a backend would call the engine" |

---

## 3. How to add a brand-new agent

Two cases: **(A)** it's basically the same reasoning loop with a different
prompt (fast, ~10 lines), or **(B)** it needs genuinely different logic
(e.g. a vision agent that sends an image, not just text).

### Case A: new prompt-flavored agent (e.g. a "CodingAgent")

This is exactly the same pattern `MathematicalAgent` uses:

```python
# agentic_engine/agents/coding_agent.py
from __future__ import annotations
from typing import Optional
from .base_agent import BaseAgent
from .reasoning_agent import ReasoningAgent
from ..schemas.task import Task
from ..schemas.response import AgentResponse
from ..tools.python_tool import PythonTool

CODING_SYSTEM_PROMPT = """You are a careful coding agent running fully offline.
Rules:
- Write correct, runnable Python. Test your code by running it via a
  ```python``` fenced block before giving a final answer.
- If it errors, read the traceback and fix it, then re-run.
- Once it works, respond with FINAL_ANSWER: followed by the final code
  and a short explanation.
"""

class CodingAgent(BaseAgent):
    name = "coding"

    def __init__(self, gateway, model: Optional[str] = None, python_tool: Optional[PythonTool] = None):
        super().__init__(gateway, model)
        self._engine = ReasoningAgent(
            gateway, model=model, python_tool=python_tool,
            system_prompt=CODING_SYSTEM_PROMPT,
        )

    def run(self, task: Task) -> AgentResponse:
        response = self._engine.run(task)
        response.agent_name = self.name
        return response
```

Then register it wherever you build the orchestrator:

```python
# in main.py (or your backend's setup code)
from agentic_engine.agents.coding_agent import CodingAgent

orchestrator.register_agent("coding", CodingAgent(gateway, model=model))
```

Now `Task(input_text=..., agent_type="coding")` routes to it. That's the
whole pattern — export it from `agents/__init__.py` too if you want it
importable the same way as the others.

### Case B: agent with genuinely different logic (e.g. VisionAgent)

Subclass `BaseAgent` directly instead of wrapping `ReasoningAgent`:

```python
# agentic_engine/agents/vision_agent.py
from .base_agent import BaseAgent
from ..schemas.task import Task, TaskStatus
from ..schemas.response import AgentResponse

class VisionAgent(BaseAgent):
    name = "vision"

    def run(self, task: Task) -> AgentResponse:
        image_path = task.context.get("image_path")
        if not image_path:
            return AgentResponse(
                task_id=task.id, agent_name=self.name,
                status=TaskStatus.FAILED, content="",
                error="task.context['image_path'] is required for vision tasks.",
            )
        # ollama's vision-capable models (e.g. "llava") accept images
        # via the `images` field on a message — you'd extend
        # OllamaGateway.chat() to accept an optional images param, or
        # call self.gateway._client.chat(...) directly here with the
        # image bytes attached.
        ...
```

Register the same way: `orchestrator.register_agent("vision", VisionAgent(gateway))`.
Call it with `Task(input_text="what's in this image?", agent_type="vision", context={"image_path": "..."})`
— that's what `context: Dict[str, Any]` on `Task` is for: passing
agent-specific extras without bloating the shared schema.

---

## 4. How to add a new tool (e.g. a file-read tool)

Same shape as `PythonTool`: a small class with a `.run(...)` method
that returns a `ToolResult`.

```python
# agentic_engine/tools/file_tool.py
from pathlib import Path
from ..schemas.tool import ToolResult

class FileReadTool:
    name = "file_read_tool"

    def __init__(self, allowed_dir: str):
        self.allowed_dir = Path(allowed_dir).resolve()

    def run(self, relative_path: str) -> ToolResult:
        target = (self.allowed_dir / relative_path).resolve()
        if self.allowed_dir not in target.parents and target != self.allowed_dir:
            return ToolResult(tool_name=self.name, success=False,
                               error="Path escapes the allowed directory.")
        try:
            return ToolResult(tool_name=self.name, success=True,
                               output=target.read_text())
        except Exception as exc:
            return ToolResult(tool_name=self.name, success=False, error=str(exc))
```

To let an agent actually use it, you'd extend `ReasoningAgent`'s
protocol: right now it only recognizes ` ```python ` blocks. You'd add
a second pattern (e.g. ` ```read_file:path/to/file``` `), detect it in
`_extract_code`-style logic, and dispatch to the right tool. This is
the main place the "iterative execution / tool calling" part of the
spec grows from — one regex/dispatch branch per new tool.

---

## 5. Things you can change without breaking anything

- **Model**: pass `model="qwen2.5"` (or whatever you've pulled) when
  constructing any agent, or change `OllamaGateway(default_model=...)`.
  Nothing else needs to change — every agent goes through the gateway.
- **Sandbox limits**: `SandboxExecutor(timeout_seconds=30, memory_mb=512)`.
- **Max reasoning steps**: `Task(..., max_steps=10)`.
- **System prompts**: edit the `SYSTEM_PROMPT` / `MATH_SYSTEM_PROMPT`
  strings directly, or pass `system_prompt=...` to `ReasoningAgent`.

## 6. Things that need a bit more care

- **The fenced-code-block protocol** (` ```python ... ``` ` = "run this",
  `FINAL_ANSWER:` = "done") is a simple convention, not something
  Ollama enforces. If a model ignores the instructions and rambles, the
  loop will just treat the ramble as the final answer (no crash, just
  a wrong-shaped answer). Tightening this (e.g. via structured JSON
  output, if the model supports it) is a reasonable place to invest
  later.
- **Concurrency**: `TaskStateStore` is a plain dict — fine for one
  process, not safe for multiple workers hitting it at once without a
  lock or a real DB.
- **Sandbox is process-level, not a container.** Fine for a hackathon
  workbench where you trust the agent's own generated code; if you
  ever run arbitrary *user-uploaded* code through it, put it behind an
  actual container first (see the note already in `executor.py`).

---

## 7. Quick reference: adding an agent, end to end

1. Create `agentic_engine/agents/your_agent.py` (Case A or B above).
2. Export it from `agentic_engine/agents/__init__.py`.
3. Instantiate it and call `orchestrator.register_agent("your_type", YourAgent(gateway))`.
4. Call it with `Task(input_text=..., agent_type="your_type")`.
5. Write a test in `tests/` using `FakeGateway` (see `tests/test_reasoning_agents.py`) —
   no real Ollama needed to test the control flow.

That's the entire extension surface. Nothing in `Orchestrator` or the
schemas needs to change for a new agent — only for a genuinely new
kind of data (e.g. `Task.context["image_path"]`, which already exists
as a free-form dict for exactly this reason).

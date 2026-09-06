# Agentic Engine Core Update

This update changes the generic engine so the Orchestrator is the decision-making brain.

Core flow:

USER -> GUARDRAILS -> ORCHESTRATOR/PLANNER -> MODEL SELECTOR -> AGENT -> TOOLS -> VALIDATOR -> OUTPUT
                                                   ^                              |
                                                   |----------- REPLAN -----------|

StateSchema (`agentic_engine/state/schema.py`) carries the workflow state.
The old keyword router is no longer part of planning.

Copy these files into the existing `agentic_engine` package, preserving the existing
supporting components such as `config.py`, `llm.py`, `sandbox.py`, `document_output.py`,
`session_store.py`, `extractors.py`, `knowledge.py`, `guardrails/`, and `validators/`.

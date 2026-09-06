"""
Standalone entrypoint for the Agentic AI Engine.

This is a bare CLI so the engine can be developed and tested in
isolation, completely decoupled from any backend/frontend. Wire the
Orchestrator into your actual backend the same way this script does:

    orchestrator.run_task(Task(input_text=..., agent_type=...))

Usage:
    python main.py
    (then type requests; prefix with "math:" to route to the
    mathematical agent, otherwise it goes to the reasoning agent)

Requirements:
    - Ollama running locally: `ollama serve`
    - A model pulled:         `ollama pull llama3.1`
"""

from __future__ import annotations

from agentic_engine.agents.mathematical_agent import MathematicalAgent
from agentic_engine.agents.reasoning_agent import ReasoningAgent
from agentic_engine.orchestrator.orchestrator import Orchestrator
from agentic_engine.schemas.task import Task
from agentic_engine.tools.gateway import OllamaGateway, OllamaGatewayError

DEFAULT_MODEL = "tinyllama"


def build_orchestrator(model: str = DEFAULT_MODEL) -> Orchestrator:
    gateway = OllamaGateway(default_model=model)
    agents = {
        "reasoning": ReasoningAgent(gateway, model=model),
        "mathematical": MathematicalAgent(gateway, model=model),
    }
    return Orchestrator(agents=agents)


def main() -> None:
    orchestrator = build_orchestrator()

    print("Sovereign AI Workbench — Agentic Engine (local, Ollama-only)")
    print(f"Default model: {DEFAULT_MODEL}")
    print("Prefix input with 'math:' to use the mathematical agent.")
    print("Ctrl+C to exit.\n")

    while True:
        try:
            user_input = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            break

        if not user_input:
            continue

        if user_input.lower().startswith("math:"):
            agent_type = "mathematical"
            user_input = user_input[len("math:") :].strip()
        else:
            agent_type = "reasoning"

        task = Task(input_text=user_input, agent_type=agent_type)

        try:
            response = orchestrator.run_task(task)
        except OllamaGatewayError as exc:
            print(f"[engine error] {exc}\n")
            continue

        if response.error:
            print(f"[{response.agent_name} FAILED] {response.error}\n")
        else:
            print(f"[{response.agent_name}]> {response.content}\n")


if __name__ == "__main__":
    main()

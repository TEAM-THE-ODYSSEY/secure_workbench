# Integration with Existing Agentic Engine

The existing repository already has:
- OllamaGateway
- ReasoningAgent
- MathematicalAgent
- Python sandbox
- Task/AgentResponse schemas

The P&ID module remains separate.

Recommended routing:
```text
Backend
  -> Orchestrator
       -> PIDReasoningAgent
       -> EvidenceAgent
       -> MathematicalAgent
```

The backend should call the P&ID module through a stable service/interface rather than importing detector internals into API routes.

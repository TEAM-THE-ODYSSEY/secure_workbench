# Local Agent Reasoning

The P&ID agent receives:
- graph facts
- topology relationships
- evidence snippets
- confidence/provenance

The agent must not manufacture pressure, flow, failure cause, or operating limits that are absent from evidence.

Integrate the existing `OllamaGateway` so all inference stays behind the local gateway.

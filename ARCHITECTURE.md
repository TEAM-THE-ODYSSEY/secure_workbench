# Combined Agentic + P&ID Architecture

```text
P&ID
  |
  +--> Vision preprocessing
  |       +--> Symbol detector (YOLO)
  |       +--> OCR (PaddleOCR)
  |       +--> Line/arrow detector (OpenCV baseline)
  |
  +--> Multimodal fusion
  |       +--> tag-to-symbol association
  |       +--> confidence + provenance
  |
  +--> P&ID Knowledge Graph
  |       +--> topology reasoning
  |       +--> physical/control semantics
  |
  +--> Evidence Store (Qdrant)
  |       +--> plant/equipment/document/revision/status filters
  |
  +--> Local Agent Reasoning (OllamaGateway)
  |       +--> P&ID reasoning
  |       +--> evidence-grounded answer
  |
  +--> Validator/Critic
          +--> high confidence -> industrial output
          +--> low confidence  -> human verification
```

The module is separate from the existing `agentic_engine` so the backend/orchestrator can route P&ID work to it without coupling API code to vision internals.

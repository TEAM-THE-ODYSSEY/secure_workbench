# P&ID Module

This module is intentionally separate from `agentic_engine`.

## Quick demo
```bash
python -m pid_engine.demo
```

## Architecture
P&ID -> preprocessing -> YOLO symbol detection + PaddleOCR + line detection -> spatial fusion -> topology -> NetworkX graph -> Qdrant evidence -> local Ollama agent -> validator -> output/human review.

## Important
The included detector/OCR adapters are real integration points, but a trained P&ID YOLO model and local Qdrant collection are not bundled. The demo uses deterministic injected detections so the architecture can be tested without those large model assets.

See `docs/` for implementation and research documentation.

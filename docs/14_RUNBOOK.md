# Runbook

## 1. Install
```bash
pip install -r requirements.txt
```

## 2. Test the deterministic P&ID pipeline
```bash
python -m pid_engine.demo
```

## 3. YOLO
Put trained weights under:
`models/pid/best.pt`

Then construct:
```python
SymbolDetector("models/pid/best.pt")
```

## 4. OCR
PaddleOCR is loaded only when the OCR adapter is used.

## 5. Qdrant
Run Qdrant locally and configure its URL in `EvidenceStore`.

## 6. LLM
Use the existing `OllamaGateway`; the P&ID reasoning agent accepts that gateway.

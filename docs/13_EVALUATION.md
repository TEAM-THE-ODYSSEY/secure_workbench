# Evaluation

Measure the pipeline separately.

## Vision
- symbol mAP / precision / recall
- OCR character/tag accuracy

## Association
- correct tag-to-symbol assignment rate

## Topology
- edge precision
- edge recall
- relationship F1
- flow-direction accuracy

## Retrieval
- Recall@k
- MRR / nDCG
- metadata-filter correctness

## Agent
- grounded-answer rate
- unsupported-claim rate
- citation/evidence coverage
- human-escalation precision

Never report only end-to-end LLM accuracy.

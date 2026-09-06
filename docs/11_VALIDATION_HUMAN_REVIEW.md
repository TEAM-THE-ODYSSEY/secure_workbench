# Validation and Human Verification

Baseline:
- aggregate object/relationship confidence
- compare with threshold
- output only when confidence is sufficient
- route low-confidence cases to human verification

Production version should use calibrated confidence, not a simple arithmetic average.

Recommended audit fields:
`model_version, drawing_id, page, object_id, evidence, confidence, decision, timestamp`

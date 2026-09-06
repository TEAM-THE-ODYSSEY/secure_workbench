# Evidence Retrieval with Qdrant

Store plant documents as chunks with metadata.

Example payload:
```json
{
  "plant": "Refinery-A",
  "equipment_tag": "P-101",
  "document_type": "Inspection Report",
  "revision": "Rev-04",
  "status": "approved"
}
```

Retrieval should combine metadata filtering with semantic/hybrid search and reranking. Latest is not automatically authoritative: approval/effective status and supersession matter.

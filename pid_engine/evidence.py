from __future__ import annotations
from typing import Any

class EvidenceStore:
    """Qdrant adapter. Keeps Qdrant optional so the P&ID graph works standalone."""
    def __init__(self, collection: str = "pid_evidence", url: str = "http://localhost:6333"):
        self.collection = collection
        self.url = url
        self.client = None

    def connect(self):
        from qdrant_client import QdrantClient
        self.client = QdrantClient(url=self.url)
        return self.client

    def filter_payload(self, plant=None, equipment_tag=None, document_type=None,
                       revision=None, status=None):
        must = []
        def add(key, value):
            if value is not None:
                must.append({"key": key, "match": {"value": value}})
        add("plant", plant); add("equipment_tag", equipment_tag)
        add("document_type", document_type); add("revision", revision); add("status", status)
        return {"must": must}

    def search(self, query_vector, limit=5, **filters):
        if self.client is None:
            self.connect()
        return self.client.search(
            collection_name=self.collection,
            query_vector=query_vector,
            query_filter=self.filter_payload(**filters),
            limit=limit,
        )

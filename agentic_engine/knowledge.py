from __future__ import annotations

from pathlib import Path
from typing import Any


class KnowledgeRetriever:
    """
    Optional local company-knowledge retrieval.

    The orchestrator can use this for company/document questions.
    If Qdrant is not configured, it returns no external knowledge rather
    than pretending that company information was retrieved.
    """

    def __init__(self, collection="company_knowledge", qdrant_path="./data/qdrant",
                 embedding_model="all-MiniLM-L6-v2"):
        self.collection = collection
        self.qdrant_path = qdrant_path
        self.embedding_model_name = embedding_model
        self._store = None

    def configure(self):
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams
            from sentence_transformers import SentenceTransformer
        except ImportError:
            return False

        Path(self.qdrant_path).mkdir(parents=True, exist_ok=True)
        self._client = QdrantClient(path=self.qdrant_path)
        self._embedder = SentenceTransformer(self.embedding_model_name)
        size = self._embedder.get_sentence_embedding_dimension()

        names = [x.name for x in self._client.get_collections().collections]
        if self.collection not in names:
            self._client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=size, distance=Distance.COSINE),
            )
        self._store = True
        return True

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        if not query.strip():
            return []
        if self._store is None and not self.configure():
            return []

        vector = self._embedder.encode(query).tolist()
        results = self._client.query_points(
            collection_name=self.collection,
            query=vector,
            limit=limit,
        ).points

        return [
            {
                "id": str(point.id),
                "score": float(point.score),
                "text": (point.payload or {}).get("text", ""),
                "metadata": (point.payload or {}).get("metadata", {}),
            }
            for point in results
        ]

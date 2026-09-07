from __future__ import annotations
from pydantic import BaseModel


class IngestResponse(BaseModel):
    document_id: str
    chunks_indexed: int


class KnowledgeDocument(BaseModel):
    document_id: str
    document_name: str
    chunks_indexed: int

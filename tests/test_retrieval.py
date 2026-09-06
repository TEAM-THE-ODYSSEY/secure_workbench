"""
Unit tests for retrieval sub-system (PgVectorStore, PostgresFTSSearch, TrustFilter, HybridSearch, BGEReranker).
"""

import pytest
from rag.chunking.semantic_chunker import Chunk
from rag.storage.pgvector import PgVectorStore
from rag.retrieval.postgres_fts import PostgresFTSSearch
from rag.retrieval.trust_filter import TrustFilter
from rag.retrieval.reranker import ReciprocalReranker
from rag.storage.postgres import TrustLevel


def test_trust_filter():
    filter_layer = TrustFilter()

    chunk_clean = Chunk(
        chunk_id="c1",
        document_id="d1",
        content="Clean SOP content for CDU-1.",
        metadata={"trust_level": TrustLevel.VERIFIED.value, "status": "ACTIVE"},
    )
    chunk_quarantine = Chunk(
        chunk_id="c2",
        document_id="d2",
        content="Malicious prompt injection text.",
        metadata={"trust_level": TrustLevel.QUARANTINED.value, "status": "QUARANTINED"},
    )
    chunk_rejected = Chunk(
        chunk_id="c3",
        document_id="d3",
        content="Rejected malware file snippet.",
        metadata={"trust_level": "REJECTED", "status": "REJECTED"},
    )


    candidates = [(chunk_clean, 0.95), (chunk_quarantine, 0.85), (chunk_rejected, 0.75)]
    filtered = filter_layer.filter_chunks(candidates)

    assert len(filtered) == 1
    assert filtered[0][0].chunk_id == "c1"


def test_pgvector_store_in_memory():
    store = PgVectorStore(dimension=3)
    chunk = Chunk(
        chunk_id="c_test",
        document_id="doc_1",
        content="Testing vector storage.",
        metadata={"unit": "CDU-1"},
    )

    vec = [1.0, 0.0, 0.0]
    store.insert_chunk_vector(chunk, vec)

    res = store.search_similar(query_vector=[0.9, 0.1, 0.0], top_k=1)
    assert len(res) == 1
    assert res[0][0].chunk_id == "c_test"
    assert res[0][1] > 0.8


def test_postgres_fts_in_memory():
    fts = PostgresFTSSearch()
    chunk1 = Chunk(chunk_id="c1", document_id="d1", content="Crude Distillation Unit CDU-1 pump P-101A operating instructions.")
    chunk2 = Chunk(chunk_id="c2", document_id="d2", content="Hydrocracker compressor K-201 gas flow rate.")

    fts.add_chunks([chunk1, chunk2])

    res = fts.search(query="P-101A pump", top_k=1)
    assert len(res) == 1
    assert res[0][0].chunk_id == "c1"


def test_reciprocal_reranker():
    reranker = ReciprocalReranker()
    chunk1 = Chunk(chunk_id="c1", document_id="d1", content="General maintenance rules for refinery pumps.")
    chunk2 = Chunk(chunk_id="c2", document_id="d2", content="P-101A Crude Feed Charge Pump pre-startup procedure in CDU-1.")

    candidates = [(chunk1, 0.8), (chunk2, 0.7)]
    reranked = reranker.rerank(query="P-101A startup procedure", candidate_chunks=candidates, top_n=2)

    assert reranked[0][0].chunk_id == "c2"


if __name__ == "__main__":
    test_trust_filter()
    test_pgvector_store_in_memory()
    test_postgres_fts_in_memory()
    test_reciprocal_reranker()
    print("ALL RETRIEVAL TESTS PASSED SUCCESSFULLY!")


"""
API integration tests for FastAPI server endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from api.server import app

client = TestClient(app)


def test_health_check_endpoint():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "online"
        assert "service" in data


def test_list_documents_endpoint():
    with TestClient(app) as client:
        response = client.get("/api/v1/documents")
        assert response.status_code == 200
        data = response.json()
        assert "total_documents" in data
        assert "documents" in data


def test_query_knowledge_endpoint():
    with TestClient(app) as client:
        query_payload = {
            "query": "What is the operating procedure for pump P-101A?",
            "top_k": 3,
            "unit": "CDU-1",
        }
        response = client.post("/api/v1/knowledge/query", json=query_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == query_payload["query"]
        assert "context_text" in data
        assert "citations" in data


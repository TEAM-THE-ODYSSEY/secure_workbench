"""
KnowledgeTool for Main AI Agent wrapping centralized RAG system.
Performs semantic vector search (pgvector) and exact keyword search (PostgreSQL FTS),
enforces security trust gate policy (TRUSTED/APPROVED/VERIFIED only), and preserves provenance.
"""

import logging
from typing import Any, Dict, List, Optional

from agent.tools.base import BaseTool
from agent.models.schemas import Citation as AgentCitation, EvidenceChunk
from rag.pipeline import RAGPipeline
from rag.retrieval.metadata_filter import FilterCondition

logger = logging.getLogger("agent.tools.knowledge_tool")

ACCEPTED_TRUST_LEVELS = {"TRUSTED", "VERIFIED", "APPROVED"}


class KnowledgeTool(BaseTool):
    """
    Knowledge Search Tool wrapping existing centralized RAGPipeline.
    Ensures zero direct DB manipulation by agent and strict TRUSTED evidence filtering.
    """

    def __init__(self, rag_pipeline: Optional[RAGPipeline] = None):
        self.pipeline = rag_pipeline or RAGPipeline()

    @property
    def name(self) -> str:
        return "knowledge_search"

    @property
    def description(self) -> str:
        return "Search centralized Knowledge Base for trusted SOPs, equipment specifications, incident reports, and maintenance records."

    def search(
        self,
        query: str,
        entity_ids: Optional[List[str]] = None,
        document_type: Optional[str] = None,
        version: Optional[str] = None,
        top_k: int = 5,
    ) -> List[EvidenceChunk]:
        """
        Execute hybrid search via existing RAG service and filter for TRUSTED chunks only.
        """
        logger.info(f"KnowledgeTool executing search for query='{query}', entities={entity_ids}")

        filters = None
        if document_type or version:
            filter_kwargs = {}
            if document_type:
                filter_kwargs["document_type"] = document_type
            if version:
                filter_kwargs["revision"] = version
            filters = FilterCondition(**filter_kwargs)

        grounded_result = self.pipeline.query_context(
            user_query=query,
            top_k=top_k,
            filters=filters,
        )

        evidence_list: List[EvidenceChunk] = []

        for citation_item in grounded_result.citations:
            def _get(field_name, default_val=None):
                if isinstance(citation_item, dict):
                    return citation_item.get(field_name, default_val)
                return getattr(citation_item, field_name, default_val)

            trust_level = str(_get("trust_level", "TRUSTED")).upper()
            if trust_level not in ACCEPTED_TRUST_LEVELS:
                logger.warning(
                    f"Discarding chunk from document {_get('document_id')} with non-TRUSTED status '{trust_level}'"
                )
                continue

            doc_id = str(_get("document_id", "doc-unknown"))
            doc_title = str(
                _get("title")
                or _get("document_title")
                or f"Document {doc_id}"
            )
            doc_ver = str(
                _get("revision")
                or _get("version")
                or _get("document_version")
                or "1.0"
            )
            section = str(_get("section_title") or _get("section") or "Main")
            page_num = int(_get("page_number") or _get("page") or 1)
            content_snippet = str(_get("snippet") or _get("content") or "")

            agent_citation = AgentCitation(
                document_id=doc_id,
                title=doc_title,
                version=doc_ver,
                section=section,
                page=page_num,
                trust_level="TRUSTED",
                snippet=content_snippet,
            )

            chunk = EvidenceChunk(
                document_id=doc_id,
                title=doc_title,
                version=doc_ver,
                section=section,
                page=page_num,
                entity_id=entity_ids[0] if entity_ids else None,
                trust_level="TRUSTED",
                content=content_snippet,
                citation=agent_citation,
            )
            evidence_list.append(chunk)

        logger.info(f"KnowledgeTool returned {len(evidence_list)} trusted evidence chunks.")
        return evidence_list

    def execute(self, **kwargs) -> Any:
        query = kwargs.get("query", "")
        entity_ids = kwargs.get("entity_ids")
        document_type = kwargs.get("document_type")
        version = kwargs.get("version")
        top_k = kwargs.get("top_k", 5)
        return self.search(
            query=query,
            entity_ids=entity_ids,
            document_type=document_type,
            version=version,
            top_k=top_k,
        )

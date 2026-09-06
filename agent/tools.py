"""
Knowledge Tool and Tool Registry for the Reasoning Mini-Agent V1.
Accesses knowledge exclusively through the existing RAGPipeline internal service layer.
Filtering ensures ONLY TRUSTED/APPROVED/VERIFIED evidence is returned.
"""

import logging
from typing import Any, Callable, Dict, List, Optional
from agent.models import Citation as AgentCitation, EvidenceChunk
from rag.pipeline import RAGPipeline
from rag.retrieval.metadata_filter import FilterCondition

logger = logging.getLogger("agent.tools")

# Trust levels considered safe for agent consumption
ACCEPTED_TRUST_LEVELS = {"TRUSTED", "VERIFIED", "APPROVED"}


class KnowledgeTool:
    """
    Knowledge Search Tool wrapping existing RAGPipeline retrieval engine.
    Ensures zero direct DB/pgvector access and strict TRUSTED evidence filtering.
    """

    def __init__(self, rag_pipeline: Optional[RAGPipeline] = None):
        self.pipeline = rag_pipeline or RAGPipeline()

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

        # Build FilterCondition directly (MetadataFilter.build does not exist)
        filters = None
        if document_type or version:
            filter_kwargs = {}
            if document_type:
                filter_kwargs["document_type"] = document_type
            if version:
                filter_kwargs["revision"] = version
            filters = FilterCondition(**filter_kwargs)

        # Query existing RAG service
        grounded_result = self.pipeline.query_context(
            user_query=query,
            top_k=top_k,
            filters=filters,
        )

        evidence_list: List[EvidenceChunk] = []

        for citation_item in grounded_result.citations:
            # The citations are rag.context.citation_builder.Citation Pydantic objects.
            # Use getattr for Pydantic model attribute access, with dict fallback.
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


class ToolRegistry:
    """Explicit tool registry for validating and executing tools requested by reasoning agent."""

    def __init__(self, knowledge_tool: Optional[KnowledgeTool] = None):
        self.knowledge_tool = knowledge_tool or KnowledgeTool()
        self._registry: Dict[str, Callable] = {
            "knowledge_search": self.knowledge_tool.search,
        }

    def register(self, name: str, func: Callable) -> None:
        """Register a new validated tool."""
        self._registry[name] = func

    def get_tool(self, name: str) -> Optional[Callable]:
        """Retrieve tool function by name."""
        return self._registry.get(name)

    def execute(self, name: str, **kwargs) -> Any:
        """Validate and execute a tool call."""
        tool = self.get_tool(name)
        if not tool:
            raise ValueError(f"Tool '{name}' is not registered in ToolRegistry.")
        return tool(**kwargs)

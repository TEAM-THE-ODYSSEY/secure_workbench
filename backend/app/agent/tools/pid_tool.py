"""
PIDTool for Main AI Agent wrapping P&ID topology queries, tag identification,
downstream/upstream relationships, isolation valves, instrument monitoring, and provenance.
"""

import logging
from typing import Any, Dict, List, Optional
from agent.tools.base import BaseTool
from agent.pid.topology import PIDTopologyEngine
from agent.models.schemas import Citation as AgentCitation, EvidenceChunk

logger = logging.getLogger("agent.tools.pid_tool")


class PIDTool(BaseTool):
    """
    P&ID Capability Tool available to Main Agent for topology & engineering tag queries.
    """

    def __init__(self, topology_engine: Optional[PIDTopologyEngine] = None):
        self.topology = topology_engine or PIDTopologyEngine()

    @property
    def name(self) -> str:
        return "pid_query"

    @property
    def description(self) -> str:
        return "Query P&ID topology diagrams for equipment tags, downstream/upstream relationships, isolation valves, flow paths, and instruments."

    def query(
        self,
        tag: str,
        query_type: str = "DOWNSTREAM",
        target_tag: Optional[str] = None,
    ) -> List[EvidenceChunk]:
        """
        Query P&ID graph for topology evidence matching target tag.
        """
        logger.info(f"PIDTool querying topology for tag='{tag}', query_type='{query_type}'")
        evidence_chunks: List[EvidenceChunk] = []

        if query_type.upper() == "ISOLATION_VALVES":
            valves = self.topology.query_isolation_valves(tag)
            for idx, v in enumerate(valves, 1):
                prov = v.get("provenance", {})
                doc_id = prov.get("document_id", "doc_PID_CDU_101")
                doc_ver = prov.get("version_id", "1.0")
                page_num = prov.get("page", 1)
                text = f"P&ID Topology Evidence: Isolation valve {v['tag']} ({v['isolation_type']}) connected to {tag} on piping line {v.get('pipe', 'N/A')} with confidence {v['confidence']}."

                cit = AgentCitation(
                    document_id=doc_id,
                    title="P&ID CDU-101 Diagram Topology",
                    version=doc_ver,
                    section="P&ID Diagram Topology",
                    page=page_num,
                    trust_level="TRUSTED",
                    snippet=text,
                )
                evidence_chunks.append(
                    EvidenceChunk(
                        document_id=doc_id,
                        title="P&ID CDU-101 Diagram Topology",
                        version=doc_ver,
                        section="P&ID Diagram Topology",
                        page=page_num,
                        entity_id=v["entity_id"],
                        trust_level="TRUSTED",
                        content=text,
                        citation=cit,
                    )
                )

        elif query_type.upper() == "FLOW_PATH" and target_tag:
            flow = self.topology.query_flow_path(tag, target_tag)
            if flow:
                flow_tags = " -> ".join([f["tag"] for f in flow])
                text = f"P&ID Topology Flow Path from {tag} to {target_tag}: {flow_tags}."
                cit = AgentCitation(
                    document_id="doc_PID_CDU_101",
                    title="P&ID CDU-101 Diagram Topology",
                    version="1.0",
                    section="P&ID Flow Path",
                    page=1,
                    trust_level="TRUSTED",
                    snippet=text,
                )
                evidence_chunks.append(
                    EvidenceChunk(
                        document_id="doc_PID_CDU_101",
                        title="P&ID CDU-101 Diagram Topology",
                        version="1.0",
                        section="P&ID Flow Path",
                        page=1,
                        entity_id=tag,
                        trust_level="TRUSTED",
                        content=text,
                        citation=cit,
                    )
                )

        else:  # DOWNSTREAM / GENERAL
            downstream = self.topology.query_downstream(tag)
            for idx, ds in enumerate(downstream, 1):
                prov = ds.get("provenance", {})
                doc_id = prov.get("document_id", "doc_PID_CDU_101")
                doc_ver = prov.get("version_id", "1.0")
                page_num = prov.get("page", 1)
                text = f"P&ID Topology Evidence: Equipment/Valve {ds['tag']} ({ds['type']}) is {ds['relationship']} of {tag} via piping line {ds.get('pipe', 'N/A')} with confidence {ds['confidence']}."

                cit = AgentCitation(
                    document_id=doc_id,
                    title="P&ID CDU-101 Diagram Topology",
                    version=doc_ver,
                    section="P&ID Diagram Topology",
                    page=page_num,
                    trust_level="TRUSTED",
                    snippet=text,
                )
                evidence_chunks.append(
                    EvidenceChunk(
                        document_id=doc_id,
                        title="P&ID CDU-101 Diagram Topology",
                        version=doc_ver,
                        section="P&ID Diagram Topology",
                        page=page_num,
                        entity_id=ds["entity_id"],
                        trust_level="TRUSTED",
                        content=text,
                        citation=cit,
                    )
                )

        logger.info(f"PIDTool returned {len(evidence_chunks)} topology evidence chunks.")
        return evidence_chunks

    def execute(self, **kwargs) -> Any:
        tag = kwargs.get("tag", kwargs.get("entity", ""))
        query_type = kwargs.get("query_type", "DOWNSTREAM")
        target_tag = kwargs.get("target_tag")
        return self.query(tag=tag, query_type=query_type, target_tag=target_tag)

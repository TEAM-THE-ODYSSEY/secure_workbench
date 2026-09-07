"""
P&ID Topology Engine for querying equipment connections, downstream/upstream flow paths,
isolation valves, instrument monitoring, and provenance.
"""

import logging
from typing import Any, Dict, List, Optional
import networkx as nx

from agent.pid.schemas import (
    PIDConnection,
    PIDDiagramKnowledge,
    PIDEntity,
    PIDSourceProvenance,
)
from agent.pid.entity_linker import PIDEntityLinker

logger = logging.getLogger("agent.pid.topology")


class PIDTopologyEngine:
    """
    Query interface over P&ID structured topology representation.
    """

    def __init__(self, entity_linker: Optional[PIDEntityLinker] = None):
        self.linker = entity_linker or PIDEntityLinker()
        self.knowledge_base: Dict[str, PIDDiagramKnowledge] = {}
        self.graph = nx.MultiDiGraph()
        self._initialize_default_topology()

    def _initialize_default_topology(self):
        """Seed default verified P&ID topology for MRPL CDU-1 unit (Crude Pump P-101A)."""
        prov = PIDSourceProvenance(
            document_id="doc_PID_CDU_101",
            version_id="1.0",
            page=1,
            title="P&ID Crude Distillation Unit CDU-101 Feed Pump System",
        )

        entities = [
            self.linker.resolve_entity("P-101A"),
            self.linker.resolve_entity("XV-101"),
            self.linker.resolve_entity("HV-101"),
            self.linker.resolve_entity("PT-101"),
            self.linker.resolve_entity("FT-102"),
            self.linker.resolve_entity("H-101"),
        ]

        connections = [
            PIDConnection(
                source_entity="EQ-P101A",
                target_entity="EQ-XV101",
                relationship="DOWNSTREAM",
                pipe="4-CR-101-CS",
                confidence=1.0,
                provenance=prov,
            ),
            PIDConnection(
                source_entity="EQ-HV101",
                target_entity="EQ-P101A",
                relationship="UPSTREAM",
                pipe="6-CR-100-CS",
                confidence=1.0,
                provenance=prov,
            ),
            PIDConnection(
                source_entity="EQ-P101A",
                target_entity="EQ-PT101",
                relationship="MONITORED_BY",
                pipe="1/2-IMP-101",
                confidence=1.0,
                provenance=prov,
            ),
            PIDConnection(
                source_entity="EQ-XV101",
                target_entity="EQ-H101",
                relationship="DOWNSTREAM",
                pipe="4-CR-102-CS",
                confidence=0.95,
                provenance=prov,
            ),
        ]

        diag = PIDDiagramKnowledge(
            diagram_id="PID-CDU-101",
            page=1,
            entities=entities,
            connections=connections,
            source=prov,
        )

        self.register_diagram(diag)

    def register_diagram(self, diagram: PIDDiagramKnowledge):
        """Register structured P&ID diagram knowledge into the graph engine."""
        self.knowledge_base[diagram.diagram_id] = diagram
        for ent in diagram.entities:
            self.graph.add_node(
                ent.id,
                tag=ent.tag,
                type=ent.type,
                confidence=ent.confidence,
                diagram_id=diagram.diagram_id,
            )
        for conn in diagram.connections:
            self.graph.add_edge(
                conn.source_entity,
                conn.target_entity,
                relationship=conn.relationship,
                pipe=conn.pipe,
                confidence=conn.confidence,
                provenance=conn.provenance.model_dump() if conn.provenance else {},
            )
        logger.info(f"Registered P&ID diagram '{diagram.diagram_id}' ({len(diagram.entities)} entities, {len(diagram.connections)} connections)")

    def query_downstream(self, target_tag: str) -> List[Dict[str, Any]]:
        """Find downstream equipment and valves connected to target tag."""
        canonical_id = self.linker.get_canonical_entity_id(target_tag)
        results = []

        if canonical_id in self.graph:
            for _, successor, data in self.graph.out_edges(canonical_id, data=True):
                succ_node = self.graph.nodes.get(successor, {})
                results.append({
                    "entity_id": successor,
                    "tag": succ_node.get("tag", successor),
                    "type": succ_node.get("type", "UNKNOWN"),
                    "relationship": data.get("relationship", "DOWNSTREAM"),
                    "pipe": data.get("pipe"),
                    "confidence": data.get("confidence", 1.0),
                    "provenance": data.get("provenance", {}),
                })
        return results

    def query_isolation_valves(self, target_tag: str) -> List[Dict[str, Any]]:
        """Find isolation valves (upstream and downstream) connected to target equipment."""
        canonical_id = self.linker.get_canonical_entity_id(target_tag)
        valves = []

        # Downstream valves
        for item in self.query_downstream(target_tag):
            if item["type"] == "VALVE":
                item["isolation_type"] = "DISCHARGE_ISOLATION"
                valves.append(item)

        # Upstream valves
        if canonical_id in self.graph:
            for predecessor, _, data in self.graph.in_edges(canonical_id, data=True):
                pred_node = self.graph.nodes.get(predecessor, {})
                if pred_node.get("type") == "VALVE":
                    valves.append({
                        "entity_id": predecessor,
                        "tag": pred_node.get("tag", predecessor),
                        "type": "VALVE",
                        "isolation_type": "SUCTION_ISOLATION",
                        "pipe": data.get("pipe"),
                        "confidence": data.get("confidence", 1.0),
                        "provenance": data.get("provenance", {}),
                    })
        return valves

    def query_flow_path(self, source_tag: str, target_tag: str) -> List[Dict[str, Any]]:
        """Find flow path from source tag to target tag."""
        src_id = self.linker.get_canonical_entity_id(source_tag)
        tgt_id = self.linker.get_canonical_entity_id(target_tag)

        if src_id not in self.graph or tgt_id not in self.graph:
            return []

        try:
            path = nx.shortest_path(self.graph, src_id, tgt_id)
            flow = []
            for node_id in path:
                node_data = self.graph.nodes.get(node_id, {})
                flow.append({
                    "entity_id": node_id,
                    "tag": node_data.get("tag", node_id),
                    "type": node_data.get("type", "UNKNOWN"),
                })
            return flow
        except nx.NetworkXNoPath:
            return []

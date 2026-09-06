from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvidenceItem:
    """
    A single piece of evidence extracted from the P&ID pipeline.
    """

    evidence_id: str
    source: str
    evidence_type: str
    text: str

    confidence: float = 0.0

    object_id: str | None = None
    target_object_id: str | None = None

    bbox: tuple | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:

        return {
            "evidence_id": self.evidence_id,
            "source": self.source,
            "evidence_type": self.evidence_type,
            "text": self.text,
            "confidence": self.confidence,
            "object_id": self.object_id,
            "target_object_id": self.target_object_id,
            "bbox": self.bbox,
            "metadata": self.metadata,
        }


class EvidenceBuilder:
    """
    Converts P&ID analysis results into structured evidence.

    Evidence sources:

        YOLO
        OCR / fused object information
        Topology
        Knowledge graph
    """

    def __init__(self):

        self.counter = 0

    # =========================================================
    # ID GENERATION
    # =========================================================

    def _next_id(self) -> str:

        self.counter += 1

        return f"evidence_{self.counter:05d}"

    # =========================================================
    # OBJECT EVIDENCE
    # =========================================================

    def _build_object_evidence(
        self,
        obj,
    ) -> EvidenceItem:

        object_type = getattr(
            obj,
            "object_type",
            "unknown",
        )

        object_id = getattr(
            obj,
            "object_id",
            None,
        )

        tag = getattr(
            obj,
            "tag",
            None,
        )

        confidence = float(
            getattr(
                obj,
                "association_confidence",
                0.0,
            )
        )

        bbox = getattr(
            obj,
            "bbox",
            None,
        )

        if tag:

            text = (
                f"P&ID object {object_id} "
                f"is a {object_type} "
                f"with tag {tag}."
            )

        else:

            text = (
                f"P&ID object {object_id} "
                f"is detected as {object_type}. "
                f"No reliable tag was associated."
            )

        return EvidenceItem(
            evidence_id=self._next_id(),
            source="fusion",
            evidence_type="object",
            text=text,
            confidence=confidence,
            object_id=object_id,
            bbox=bbox,
            metadata={
                "object_type": object_type,
                "tag": tag,
            },
        )

    # =========================================================
    # LINE EVIDENCE
    # =========================================================

    def _build_line_evidence(
        self,
        line,
    ) -> EvidenceItem:

        line_id = getattr(
            line,
            "line_id",
            "unknown_line",
        )

        line_type = getattr(
            line,
            "line_type",
            "unknown",
        )

        confidence = float(
            getattr(
                line,
                "confidence",
                0.0,
            )
        )

        points = getattr(
            line,
            "points",
            None,
        )

        text = (
            f"Detected {line_type} "
            f"{line_id} in the P&ID."
        )

        return EvidenceItem(
            evidence_id=self._next_id(),
            source="line_detector",
            evidence_type="line",
            text=text,
            confidence=confidence,
            metadata={
                "line_id": line_id,
                "line_type": line_type,
                "points": points,
            },
        )

    # =========================================================
    # RELATIONSHIP EVIDENCE
    # =========================================================

    def _build_relationship_evidence(
        self,
        relationship,
    ) -> EvidenceItem:

        source = getattr(
            relationship,
            "source",
            None,
        )

        target = getattr(
            relationship,
            "target",
            None,
        )

        relation_type = getattr(
            relationship,
            "relationship",
            "related_to",
        )

        pipe = getattr(
            relationship,
            "pipe",
            None,
        )

        confidence = float(
            getattr(
                relationship,
                "confidence",
                0.0,
            )
        )

        evidence = getattr(
            relationship,
            "evidence",
            [],
        )

        text = (
            f"P&ID object {source} "
            f"is {relation_type} "
            f"{target}."
        )

        return EvidenceItem(
            evidence_id=self._next_id(),
            source="topology",
            evidence_type="relationship",
            text=text,
            confidence=confidence,
            object_id=source,
            target_object_id=target,
            metadata={
                "relationship": relation_type,
                "pipe": pipe,
                "topology_evidence": evidence,
            },
        )

    # =========================================================
    # GRAPH EVIDENCE
    # =========================================================

    def _build_graph_evidence(
        self,
        graph,
    ) -> list[EvidenceItem]:

        results = []

        if not graph:
            return results

        # Handle dictionary-style graphs
        if isinstance(graph, dict):

            nodes = graph.get(
                "nodes",
                [],
            )

            edges = graph.get(
                "edges",
                [],
            )

            for node in nodes:

                text = (
                    f"Knowledge graph node: "
                    f"{node}"
                )

                results.append(
                    EvidenceItem(
                        evidence_id=self._next_id(),
                        source="knowledge_graph",
                        evidence_type="graph_node",
                        text=text,
                        metadata={
                            "node": node,
                        },
                    )
                )

            for edge in edges:

                text = (
                    f"Knowledge graph relationship: "
                    f"{edge}"
                )

                results.append(
                    EvidenceItem(
                        evidence_id=self._next_id(),
                        source="knowledge_graph",
                        evidence_type="graph_edge",
                        text=text,
                        metadata={
                            "edge": edge,
                        },
                    )
                )

        return results

    # =========================================================
    # BUILD ALL EVIDENCE
    # =========================================================

    def build(
        self,
        analysis,
    ) -> list[EvidenceItem]:
        """
        Convert a PIDAnalysisResult into evidence items.
        """

        self.counter = 0

        evidence = []

        # -----------------------------------------------------
        # Objects
        # -----------------------------------------------------

        objects = getattr(
            analysis,
            "objects",
            [],
        )

        for obj in objects:

            evidence.append(
                self._build_object_evidence(
                    obj
                )
            )

        # -----------------------------------------------------
        # Lines
        # -----------------------------------------------------

        lines = getattr(
            analysis,
            "lines",
            [],
        )

        for line in lines:

            evidence.append(
                self._build_line_evidence(
                    line
                )
            )

        # -----------------------------------------------------
        # Relationships
        # -----------------------------------------------------

        relationships = getattr(
            analysis,
            "relationships",
            [],
        )

        for relationship in relationships:

            evidence.append(
                self._build_relationship_evidence(
                    relationship
                )
            )

        # -----------------------------------------------------
        # Graph
        # -----------------------------------------------------

        graph = getattr(
            analysis,
            "graph",
            None,
        )

        evidence.extend(
            self._build_graph_evidence(
                graph
            )
        )

        return evidence

    # =========================================================
    # CONVENIENCE
    # =========================================================

    def build_dicts(
        self,
        analysis,
    ) -> list[dict[str, Any]]:

        return [
            item.to_dict()
            for item in self.build(
                analysis
            )
        ]
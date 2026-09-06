from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from .models import PIDAnalysisResult
from .preprocessing import preprocess_image
from .fusion import SpatialFusion
from .topology import TopologyEngine
from .graph import PIDGraph

@dataclass
class PIDPipeline:
    symbol_detector: Any
    ocr: Any
    line_detector: Any
    fusion: SpatialFusion = field(default_factory=SpatialFusion)
    topology: TopologyEngine = field(default_factory=TopologyEngine)

    def analyze(self, image: Any) -> PIDAnalysisResult:
        gray = preprocess_image(image)
        symbols = self.symbol_detector.detect(image)
        texts = self.ocr.detect(image)
        lines = self.line_detector.detect(gray)
        objects = self.fusion.fuse(symbols, texts)
        relationships = self.topology.build_relationships(objects, lines)

        graph = PIDGraph()
        for obj in objects:
            graph.add_object(obj)
        for rel in relationships:
            graph.add_relationship(rel)

        warnings = []
        for obj in objects:
            if obj.association_confidence < 0.60:
                warnings.append(f"Low-confidence association: {obj.object_id} ({obj.tag})")
        for rel in relationships:
            if rel.confidence < 0.70:
                warnings.append(f"Low-confidence relationship: {rel.source}->{rel.target}")

        return PIDAnalysisResult(
            objects=objects,
            lines=lines,
            relationships=relationships,
            graph=graph.to_dict(),
            warnings=warnings,
        )

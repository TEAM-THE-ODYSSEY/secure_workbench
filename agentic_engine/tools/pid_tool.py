from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class PIDToolResult:
    success: bool
    summary: str
    objects: List[Dict[str, Any]] = field(default_factory=list)
    lines: List[Dict[str, Any]] = field(default_factory=list)
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    graph: Dict[str, Any] = field(default_factory=dict)
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    confidence: float = 0.0
    decision: str = "output"  # "output" or "human_verification"
    xlsx_path: Optional[str] = None
    error: Optional[str] = None


class PIDTool:
    """Specialized Domain Adapter for Piping & Instrumentation Diagrams (P&ID)."""

    def __init__(self, model_path: Optional[str] = None, conf_threshold: float = 0.70):
        self.conf_threshold = conf_threshold
        self.model_path = model_path or self._resolve_model_path()
        self._pipeline = None

    @staticmethod
    def _resolve_model_path() -> str:
        candidates = [
            "models/best.pt",
            "../models/best.pt",
            os.path.join(os.path.dirname(__file__), "../../models/best.pt"),
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
        return "models/best.pt"

    def _get_pipeline(self):
        if self._pipeline is not None:
            return self._pipeline
        try:
            from pid_engine.symbol_detector import SymbolDetector
            from pid_engine.ocr import OCRAdapter
            from pid_engine.line_detector import LineDetector
            from pid_engine.pipeline import PIDPipeline

            detector = SymbolDetector(weights=self.model_path, conf=0.25)
            ocr = OCRAdapter()
            line_detector = LineDetector()
            self._pipeline = PIDPipeline(symbol_detector=detector, ocr=ocr, line_detector=line_detector)
            return self._pipeline
        except Exception as e:
            raise RuntimeError(f"Failed to initialize P&ID domain pipeline: {e}")

    def analyze(self, image_path: str, generate_excel: bool = False, output_dir: str = "./data/outputs") -> PIDToolResult:
        p = Path(image_path)
        if not p.exists():
            return PIDToolResult(
                success=False,
                summary=f"P&ID image not found at: {image_path}",
                error=f"File not found: {image_path}",
            )

        try:
            from pid_engine.preprocessing import load_image
            from pid_engine.agents import PIDValidator

            image = load_image(str(p))
            pipeline = self._get_pipeline()
            analysis = pipeline.analyze(image)

            validator = PIDValidator(threshold=self.conf_threshold)
            val_result = validator.validate(analysis)

            objects_data = [
                {
                    "object_id": o.object_id,
                    "type": o.object_type,
                    "tag": o.tag,
                    "bbox": getattr(o, "bbox", []),
                    "confidence": round(float(getattr(o, "association_confidence", 0.0)), 3),
                }
                for o in analysis.objects
            ]

            lines_data = [
                {
                    "line_id": l.line_id,
                    "type": l.line_type,
                    "confidence": round(float(l.confidence), 3),
                }
                for l in analysis.lines
            ]

            rel_data = [
                {
                    "source": r.source,
                    "target": r.target,
                    "relationship": r.relationship,
                    "pipe": r.pipe,
                    "confidence": round(float(r.confidence), 3),
                }
                for r in analysis.relationships
            ]

            evidence_data = [
                {
                    "entity": o.object_id,
                    "tag": o.tag,
                    "type": o.object_type,
                    "evidence_type": "spatial_detection",
                    "confidence": round(float(getattr(o, "association_confidence", 0.0)), 3),
                }
                for o in analysis.objects
            ]

            # Generate formatted technical summary
            summary_lines = [
                "### P&ID Engineering Analysis Report",
                f"- **Total Components Detected**: {len(analysis.objects)}",
                f"- **Process Lines Detected**: {len(analysis.lines)}",
                f"- **Topology Connections Established**: {len(analysis.relationships)}",
                f"- **Average Detection & Association Confidence**: {val_result['confidence'] * 100:.1f}%",
                f"- **Quality Gate Decision**: {val_result['decision'].upper()}",
                "",
                "#### Detected Equipment & Instruments:",
            ]
            for o in objects_data[:15]:
                summary_lines.append(f"  - `{o['object_id']}` [{o['type']}] Tag: **{o['tag']}** (Conf: {o['confidence']})")
            if len(objects_data) > 15:
                summary_lines.append(f"  - ... and {len(objects_data) - 15} more components.")

            summary_lines.append("\n#### Verified Topological Connections:")
            for r in rel_data[:15]:
                summary_lines.append(f"  - `{r['source']}` ──► `{r['target']}` (Pipe: {r['pipe']}, Conf: {r['confidence']})")
            if len(rel_data) > 15:
                summary_lines.append(f"  - ... and {len(rel_data) - 15} more connections.")

            if analysis.warnings:
                summary_lines.append("\n#### Engineering Verification Warnings:")
                for w in analysis.warnings:
                    summary_lines.append(f"  - ⚠️ {w}")
                if val_result["decision"] == "human_verification":
                    summary_lines.append("\n> [!WARNING]\n> Low confidence detected in topology associations. Manual engineering review required.")

            xlsx_file = None
            if generate_excel:
                xlsx_file = self._create_excel_report(p.stem, objects_data, lines_data, rel_data, output_dir)

            return PIDToolResult(
                success=True,
                summary="\n".join(summary_lines),
                objects=objects_data,
                lines=lines_data,
                relationships=rel_data,
                graph=analysis.graph,
                evidence=evidence_data,
                warnings=analysis.warnings,
                confidence=val_result["confidence"],
                decision=val_result["decision"],
                xlsx_path=xlsx_file,
            )
        except Exception as e:
            return PIDToolResult(
                success=False,
                summary=f"P&ID analysis failed: {e}",
                error=str(e),
            )

    @staticmethod
    def _create_excel_report(stem: str, objects: list, lines: list, rels: list, output_dir: str) -> str:
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment

            wb = Workbook()
            # 1. Equipment Sheet
            ws_eq = wb.active
            ws_eq.title = "Equipment & Instruments"
            headers_eq = ["Object ID", "Component Type", "Equipment Tag", "Association Confidence"]
            ws_eq.append(headers_eq)
            for o in objects:
                ws_eq.append([o["object_id"], o["type"], o["tag"], o["confidence"]])

            # 2. Process Lines Sheet
            ws_ln = wb.create_sheet(title="Process Lines")
            ws_ln.append(["Line ID", "Line Type", "Confidence"])
            for l in lines:
                ws_ln.append([l["line_id"], l["type"], l["confidence"]])

            # 3. Topology Connections Sheet
            ws_rel = wb.create_sheet(title="Topology Connections")
            ws_rel.append(["Source Component", "Target Component", "Relationship", "Line Identifier", "Confidence"])
            for r in rels:
                ws_rel.append([r["source"], r["target"], r["relationship"], r["pipe"], r["confidence"]])

            # Style header rows
            header_fill = PatternFill(start_color="1A365D", end_color="1A365D", fill_type="solid")
            header_font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
            for sheet in [ws_eq, ws_ln, ws_rel]:
                for cell in sheet[1]:
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                sheet.freeze_panes = "A2"

            out_path = Path(output_dir) / f"{stem}_pid_topology.xlsx"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            wb.save(out_path)
            return str(out_path.resolve())
        except Exception:
            return ""

from __future__ import annotations

import csv
from pathlib import Path


class DocumentOutput:
    """Create final user-requested document formats from the verified answer."""

    def __init__(self, output_dir="./data/outputs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create(self, filename: str, content: str, fmt: str) -> str:
        fmt = fmt.lower().lstrip(".")
        safe = Path(filename).stem or "answer"

        if fmt in {"doc", "docx", "word"}:
            from docx import Document
            path = self.output_dir / f"{safe}.docx"
            doc = Document()
            doc.add_heading(safe, level=1)
            for block in content.split("\n\n"):
                if block.strip():
                    doc.add_paragraph(block.strip())
            doc.save(path)
            return str(path)

        if fmt == "pdf":
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            path = self.output_dir / f"{safe}.pdf"
            doc = SimpleDocTemplate(str(path), pagesize=A4)
            styles = getSampleStyleSheet()
            story = []
            for block in content.split("\n\n"):
                if block.strip():
                    story.append(Paragraph(block.strip().replace("\n", "<br/>"),
                                           styles["BodyText"]))
                    story.append(Spacer(1, 10))
            doc.build(story)
            return str(path)

        if fmt == "csv":
            path = self.output_dir / f"{safe}.csv"
            with path.open("w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerows([["answer"], [content]])
            return str(path)

        if fmt in {"xlsx", "excel"}:
            from openpyxl import Workbook
            path = self.output_dir / f"{safe}.xlsx"
            wb = Workbook()
            ws = wb.active
            ws.title = "Answer"
            ws["A1"] = "Answer"
            ws["A2"] = content
            ws.column_dimensions["A"].width = 100
            wb.save(path)
            return str(path)

        raise ValueError(f"Unsupported output format: {fmt}")

from __future__ import annotations

import csv
import re
from pathlib import Path


class DocumentOutput:
    """Creates enterprise-grade user-requested document formats (XLSX, PDF, DOCX, CSV)
    from verified agent answers.
    """

    def __init__(self, output_dir: str = "./data/outputs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create(self, filename: str, content: str, fmt: str) -> str:
        fmt = fmt.lower().lstrip(".")
        safe = Path(filename).stem or "agent_output"

        if fmt in {"doc", "docx", "word"}:
            return self._create_docx(safe, content)

        if fmt == "pdf":
            return self._create_pdf(safe, content)

        if fmt == "csv":
            return self._create_csv(safe, content)

        if fmt in {"xlsx", "excel"}:
            return self._create_xlsx(safe, content)

        raise ValueError(f"Unsupported output format: {fmt}")

    def _create_docx(self, stem: str, content: str) -> str:
        from docx import Document
        from docx.shared import Inches, Pt, RGBColor

        path = self.output_dir / f"{stem}.docx"
        doc = Document()

        # Document Header Title
        title_p = doc.add_heading(stem.replace("_", " ").title(), level=0)
        doc.add_paragraph("MRPL SOVEREIGN KNOWLEDGE BASE — VERIFIED EXECUTIVE OUTPUT")

        for block in content.split("\n\n"):
            b = block.strip()
            if not b:
                continue
            if b.startswith("### "):
                doc.add_heading(b[4:], level=2)
            elif b.startswith("## "):
                doc.add_heading(b[3:], level=1)
            elif b.startswith("# "):
                doc.add_heading(b[2:], level=1)
            elif b.startswith("- ") or b.startswith("* "):
                for line in b.splitlines():
                    clean_line = re.sub(r"^\s*[-*]\s+", "", line)
                    doc.add_paragraph(clean_line, style="List Bullet")
            else:
                doc.add_paragraph(b)

        doc.save(path)
        return str(path.resolve())

    def _create_pdf(self, stem: str, content: str) -> str:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.pdfgen import canvas
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        class SovereignCanvas(canvas.Canvas):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._saved_page_states = []

            def showPage(self):
                self._saved_page_states.append(dict(self.__dict__))
                self._startPage()

            def save(self):
                num_pages = len(self._saved_page_states)
                for state in self._saved_page_states:
                    self.__dict__.update(state)
                    self.saveState()
                    self.setFont("Helvetica", 8)
                    self.setFillColor(colors.HexColor("#718096"))
                    self.setStrokeColor(colors.HexColor("#CBD5E0"))
                    self.setLineWidth(0.5)
                    self.line(36, 36, 576, 36)
                    self.drawString(36, 24, "MRPL SOVEREIGN WORKBENCH — STRICTLY GROUNDED ENTERPRISE OUTPUT")
                    self.drawRightString(576, 24, f"Page {self._pageNumber} of {num_pages}")
                    self.restoreState()
                    super().showPage()
                super().save()

        path = self.output_dir / f"{stem}.pdf"
        doc = SimpleDocTemplate(
            str(path),
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=40,
            bottomMargin=45,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#1A365D"),
        )
        sub_style = ParagraphStyle(
            "DocSub",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#4A5568"),
        )
        h2_style = ParagraphStyle(
            "DocH2",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#2B6CB0"),
        )
        body_style = ParagraphStyle(
            "DocBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#2D3748"),
        )
        bullet_style = ParagraphStyle(
            "DocBullet",
            parent=body_style,
            leftIndent=15,
            firstLineIndent=-10,
        )

        story = [
            Paragraph(stem.replace("_", " ").title(), title_style),
            Paragraph("Enterprise Multi-Agent Analysis Report &middot; Confidential & Sovereign", sub_style),
            Spacer(1, 15),
        ]

        for block in content.split("\n\n"):
            b = block.strip()
            if not b:
                continue
            if b.startswith("### "):
                story.append(Paragraph(b[4:], h2_style))
                story.append(Spacer(1, 6))
            elif b.startswith("## ") or b.startswith("# "):
                story.append(Paragraph(b.lstrip("# ").strip(), h2_style))
                story.append(Spacer(1, 6))
            elif b.startswith("- ") or b.startswith("* "):
                for line in b.splitlines():
                    clean_line = re.sub(r"^\s*[-*•]\s+", "&bull; ", line)
                    story.append(Paragraph(clean_line.replace("\n", "<br/>"), bullet_style))
                    story.append(Spacer(1, 3))
            else:
                clean_p = b.replace("\n", "<br/>")
                clean_p = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", clean_p)
                clean_p = re.sub(r"`(.*?)`", r"<font face='Courier'>\1</font>", clean_p)
                story.append(Paragraph(clean_p, body_style))
                story.append(Spacer(1, 8))

        doc.build(story, canvasmaker=SovereignCanvas)
        return str(path.resolve())

    def _create_csv(self, stem: str, content: str) -> str:
        path = self.output_dir / f"{stem}.csv"
        # Check if content has tabular lines
        table_rows = []
        for line in content.splitlines():
            if "|" in line:
                cells = [c.strip() for c in line.split("|")]
                # Strip leading/trailing empty cells from markdown | a | b |
                if cells and not cells[0]:
                    cells = cells[1:]
                if cells and not cells[-1]:
                    cells = cells[:-1]
                if cells and not all(re.match(r"^:?-+:?$", c) for c in cells):
                    table_rows.append(cells)

        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if table_rows:
                writer.writerows(table_rows)
            else:
                writer.writerows([["Output Text"], [content]])

        return str(path.resolve())

    def _create_xlsx(self, stem: str, content: str) -> str:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
        from openpyxl.utils import get_column_letter

        path = self.output_dir / f"{stem}.xlsx"
        wb = Workbook()
        ws = wb.active
        ws.title = "Analysis Report"

        # Check for markdown table in content
        table_rows = []
        regular_lines = []
        for line in content.splitlines():
            if "|" in line:
                cells = [c.strip() for c in line.split("|")]
                if cells and not cells[0]:
                    cells = cells[1:]
                if cells and not cells[-1]:
                    cells = cells[:-1]
                # Skip markdown separator line e.g. |---|---|
                if cells and not all(re.match(r"^:?-+:?$", c) for c in cells):
                    table_rows.append(cells)
            else:
                if line.strip():
                    regular_lines.append(line.strip())

        header_fill = PatternFill(start_color="1A365D", end_color="1A365D", fill_type="solid")
        header_font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
        regular_font = Font(name="Arial", size=9)
        thin_border = Border(
            left=Side(style="thin", color="E2E8F0"),
            right=Side(style="thin", color="E2E8F0"),
            top=Side(style="thin", color="E2E8F0"),
            bottom=Side(style="thin", color="E2E8F0"),
        )

        if table_rows:
            # Write structured table
            for r_idx, row in enumerate(table_rows, start=1):
                for c_idx, val in enumerate(row, start=1):
                    cell = ws.cell(row=r_idx, column=c_idx, value=val)
                    cell.border = thin_border
                    if r_idx == 1:
                        cell.fill = header_fill
                        cell.font = header_font
                        cell.alignment = Alignment(horizontal="center", vertical="center")
                    else:
                        cell.font = regular_font
                        cell.alignment = Alignment(vertical="center")

            # Add context notes below table
            if regular_lines:
                start_note = len(table_rows) + 2
                ws.cell(row=start_note, column=1, value="Report Notes:").font = Font(bold=True)
                for idx, note in enumerate(regular_lines[:15], start=start_note + 1):
                    ws.cell(row=idx, column=1, value=note).font = regular_font

            ws.freeze_panes = "A2"
        else:
            # Itemized summary lines
            ws.cell(row=1, column=1, value="Report Title").fill = header_fill
            ws.cell(row=1, column=1).font = header_font
            ws.cell(row=1, column=2, value=stem.replace("_", " ").title()).font = Font(bold=True)

            ws.cell(row=3, column=1, value="Section / Item").fill = header_fill
            ws.cell(row=3, column=1).font = header_font
            ws.cell(row=3, column=2, value="Details").fill = header_fill
            ws.cell(row=3, column=2).font = header_font

            curr_row = 4
            for line in regular_lines:
                if line.startswith("- ") or line.startswith("* "):
                    parts = line.lstrip("-* ").split(":", 1)
                    if len(parts) == 2:
                        ws.cell(row=curr_row, column=1, value=parts[0].strip()).font = Font(bold=True)
                        ws.cell(row=curr_row, column=2, value=parts[1].strip()).font = regular_font
                    else:
                        ws.cell(row=curr_row, column=1, value=f"Item {curr_row-3}")
                        ws.cell(row=curr_row, column=2, value=line.lstrip("-* ").strip()).font = regular_font
                    curr_row += 1
                elif line.startswith("#"):
                    curr_row += 1
                    header_cell = ws.cell(row=curr_row, column=1, value=line.lstrip("#").strip())
                    header_cell.font = Font(bold=True, size=11, color="1A365D")
                    curr_row += 1
                else:
                    ws.cell(row=curr_row, column=1, value="Content")
                    ws.cell(row=curr_row, column=2, value=line).font = regular_font
                    curr_row += 1

        # Adjust column widths automatically
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 70)

        wb.save(path)
        return str(path.resolve())

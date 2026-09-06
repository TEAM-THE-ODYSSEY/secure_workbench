"""
ReportLab PDF Generator for the Reasoning Mini-Agent V1.
Renders validated StructuredPDFContent into an executive, enterprise-grade PDF document.
"""

from datetime import datetime, timezone
import io
import logging
from typing import Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from agent.models import StructuredPDFContent

logger = logging.getLogger("agent.pdf_generator")


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and render total page count,
    running headers, and enterprise footer notice on every page.
    """

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
            self.draw_header_footer(num_pages)
            super().showPage()
        super().save()

    def draw_header_footer(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#718096"))

        # Footer divider line
        self.setStrokeColor(colors.HexColor("#CBD5E0"))
        self.setLineWidth(0.5)
        self.line(36, 36, 576, 36)

        # Footer Text
        footer_text = "MRPL SOVEREIGN KNOWLEDGE BASE — STRICTLY GROUNDED ENTERPRISE DOCUMENT"
        page_text = f"Page {self._pageNumber} of {page_count}"

        self.drawString(36, 24, footer_text)
        self.drawRightString(576, 24, page_text)
        self.restoreState()


class ReportLabPDFGenerator:
    """
    Generates professional executive PDF documents from structured Pydantic model data.
    """

    def generate(
        self,
        content: StructuredPDFContent,
        task_id: str,
        model_name: str,
        fallback_used: bool = False,
    ) -> bytes:
        """
        Build and return raw PDF bytes for the given structured content.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=45,
            bottomMargin=45,
        )

        styles = getSampleStyleSheet()

        # Custom typography styles
        doc_header_style = ParagraphStyle(
            "DocHeaderTitle",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=colors.HexColor("#FFFFFF"),
            alignment=0,
        )

        doc_sub_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#E2E8F0"),
            alignment=0,
        )

        meta_label_style = ParagraphStyle(
            "MetaLabel",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#1A365D"),
        )

        meta_val_style = ParagraphStyle(
            "MetaVal",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#2D3748"),
        )

        h2_style = ParagraphStyle(
            "SectionH2",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#0F2942"),
            spaceBefore=12,
            spaceAfter=6,
        )

        body_style = ParagraphStyle(
            "BodyTextCustom",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#2D3748"),
            spaceAfter=4,
        )

        warning_style = ParagraphStyle(
            "WarningCustom",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#9B2C2C"),
        )

        citation_style = ParagraphStyle(
            "CitationCustom",
            parent=styles["Italic"],
            fontName="Helvetica-Oblique",
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#4A5568"),
        )

        table_header_style = ParagraphStyle(
            "TableHeader",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#FFFFFF"),
        )

        story = []

        # 1. Executive Banner Header
        header_text = f"<b>MANGALORE REFINERY AND PETROCHEMICALS LIMITED (MRPL)</b><br/>"
        header_text += f"<font size=14><b>{content.title.upper()}</b></font>"
        
        banner_table = Table(
            [[Paragraph(header_text, doc_header_style)]],
            colWidths=[540],
        )
        banner_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0F2942")),
                ("PADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
            ])
        )
        story.append(banner_table)
        story.append(HRFlowable(width="100%", thickness=3, color=colors.HexColor("#D4AF37"), spaceAfter=8))

        # 2. Document Control Metadata Table Grid
        timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        engine_display = f"{model_name} ('Fallback Direct Synthesis')" if fallback_used else model_name

        meta_grid = [
            [
                Paragraph("Document Task ID:", meta_label_style),
                Paragraph(task_id, meta_val_style),
                Paragraph("Classification:", meta_label_style),
                Paragraph("RESTRICTED / TRUSTED", meta_val_style),
            ],
            [
                Paragraph("Generation Date:", meta_label_style),
                Paragraph(timestamp_str, meta_val_style),
                Paragraph("Reasoning Engine:", meta_label_style),
                Paragraph(engine_display, meta_val_style),
            ],
        ]
        meta_table = Table(meta_grid, colWidths=[100, 170, 100, 170])
        meta_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7FAFC")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E0")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                ("PADDING", (0, 0), (-1, -1), 5),
            ])
        )
        story.append(meta_table)
        story.append(Spacer(1, 10))

        # 3. Purpose & Scope
        story.append(Paragraph("1. PURPOSE & OBJECTIVE", h2_style))
        story.append(Paragraph(content.purpose, body_style))

        story.append(Paragraph("2. SCOPE & BOUNDARIES", h2_style))
        story.append(Paragraph(content.scope, body_style))

        # 4. Preconditions & Safety Requirements
        if content.preconditions:
            story.append(Paragraph("3. PRE-STARTUP CHECKLIST & PRECONDITIONS", h2_style))
            for item in content.preconditions:
                story.append(Paragraph(f"• {item}", body_style))

        if content.safety_requirements:
            story.append(Paragraph("4. MANDATORY SAFETY & PPE REQUIREMENTS", h2_style))
            safety_cells = [[Paragraph(f"<b>SAFETY REQUIREMENT:</b> {req}", body_style)] for req in content.safety_requirements]
            safety_table = Table(safety_cells, colWidths=[540])
            safety_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEFCBF")),
                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#D69E2E")),
                    ("PADDING", (0, 0), (-1, -1), 6),
                ])
            )
            story.append(safety_table)
            story.append(Spacer(1, 8))

        # 5. Operating Limits
        if content.operating_limits:
            story.append(Paragraph("5. CRITICAL OPERATING LIMITS & BOUNDARIES", h2_style))
            op_data = [[
                Paragraph("Parameter", table_header_style),
                Paragraph("Grounded Boundary / Value", table_header_style),
                Paragraph("Citation Reference", table_header_style),
            ]]
            for limit in content.operating_limits:
                cit_str = ", ".join([f"{c.document_id} (p.{c.page or 1})" for c in limit.citations]) or "N/A"
                op_data.append([
                    Paragraph(f"<b>{limit.parameter}</b>", body_style),
                    Paragraph(limit.value, body_style),
                    Paragraph(cit_str, citation_style),
                ])
            op_table = Table(op_data, colWidths=[150, 200, 190])
            op_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F2942")),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
                    ("PADDING", (0, 0), (-1, -1), 5),
                ])
            )
            story.append(op_table)
            story.append(Spacer(1, 10))

        # 6. Warnings Callout
        if content.warnings:
            story.append(Paragraph("CRITICAL CAUTIONS & WARNINGS", h2_style))
            warn_cells = [[Paragraph(f"<b>WARNING:</b> {w}", warning_style)] for w in content.warnings]
            warn_table = Table(warn_cells, colWidths=[540])
            warn_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF5F5")),
                    ("BOX", (0, 0), (-1, -1), 1.5, colors.HexColor("#E53E3E")),
                    ("PADDING", (0, 0), (-1, -1), 7),
                ])
            )
            story.append(warn_table)
            story.append(Spacer(1, 10))

        # 7. Procedure Steps
        if content.procedure_steps:
            story.append(Paragraph("6. STANDARD OPERATING PROCEDURE STEPS", h2_style))
            proc_data = [[
                Paragraph("Step #", table_header_style),
                Paragraph("Instruction / Execution Detail", table_header_style),
                Paragraph("Source Citation", table_header_style),
            ]]
            for idx, step in enumerate(content.procedure_steps):
                cit_text = ""
                if step.citations:
                    c_list = [f"[{c.title}, Sec: {c.section or 'Main'}, p.{c.page or 1}]" for c in step.citations]
                    cit_text = "<br/>".join(c_list)
                proc_data.append([
                    Paragraph(f"<b>{step.step_number}</b>", body_style),
                    Paragraph(step.instruction, body_style),
                    Paragraph(cit_text, citation_style),
                ])
            
            proc_table = Table(proc_data, colWidths=[45, 315, 180])
            table_styles = [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F2942")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
            # Zebra striping for procedure table
            for row_idx in range(1, len(proc_data)):
                if row_idx % 2 == 0:
                    table_styles.append(("BACKGROUND", (0, row_idx), (-1, row_idx), colors.HexColor("#F7FAFC")))
            
            proc_table.setStyle(TableStyle(table_styles))
            story.append(proc_table)
            story.append(Spacer(1, 12))

        # 8. References & Citations Audit Trail
        story.append(Paragraph("7. TRUSTED KNOWLEDGE EVIDENCE AUDIT TRAIL", h2_style))
        if content.references:
            for ref in content.references:
                ref_line = (
                    f"• <b>{ref.title}</b> (Doc ID: <code>{ref.document_id}</code>, Ver: {ref.version}, "
                    f"Section: {ref.section or 'General'}, Page: {ref.page or 1}, Status: <b>{ref.trust_level}</b>)"
                )
                story.append(Paragraph(ref_line, citation_style))
                story.append(Spacer(1, 3))
        else:
            story.append(Paragraph("No direct citations provided.", citation_style))

        doc.build(story, canvasmaker=NumberedCanvas)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        logger.info(f"ReportLab successfully rendered executive enterprise PDF document ({len(pdf_bytes)} bytes).")
        return pdf_bytes

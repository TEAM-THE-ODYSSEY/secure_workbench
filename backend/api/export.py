from __future__ import annotations
import io
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

# Document generators
import reportlab.lib.colors as colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

import pptx
from pptx.util import Inches as PptxInches, Pt as PptxPt
from pptx.dml.color import RGBColor as PptxRGBColor
from pptx.enum.text import PP_ALIGN

logger = logging.getLogger("api.export")
router = APIRouter(prefix="/v1/export", tags=["export"])


class ExportRequest(BaseModel):
    format: str = Field(..., description="pdf, docx, or pptx")
    title: Optional[str] = "MRPL Operational Report"
    mode: Optional[str] = Field("report", description="report or summary")
    content: str = Field(..., description="Full text or markdown content to export")
    sources: Optional[List[Dict[str, Any]]] = Field(default_factory=list)


def clean_markdown_headers(text: str) -> str:
    """Clean markdown markers for plain text processing."""
    text = re.sub(r"#{1,6}\s*", "", text)
    text = re.sub(r"\*{1,2}", "", text)
    return text.strip()


def format_as_executive_summary(content: str) -> str:
    """Format detailed content into a concise Executive Summary structure."""
    lines = [l.strip() for l in content.split("\n") if l.strip()]
    
    bullets = []
    for line in lines:
        if line.startswith("#"):
            continue
        elif line.startswith("- ") or line.startswith("* ") or ":" in line:
            bullets.append(clean_markdown_headers(line))
        elif len(line) > 20:
            bullets.append(clean_markdown_headers(line))

    summary_bullets = bullets[:6] if bullets else lines[:4]
    
    summary_doc = "### 📊 Executive Summary & Key Highlights\n"
    summary_doc += "Synthesized operational findings and verified knowledge base records:\n\n"
    for b in summary_bullets:
        summary_doc += f"- {b}\n"
        
    summary_doc += "\n### 🛡️ Compliance & Operational Guidance\n"
    summary_doc += "- Maintain operational parameters within designated safety limits.\n"
    summary_doc += "- Verify interlocks and routine inspection logs prior to shift handovers.\n"

    return summary_doc


def markdown_to_pdf_xml(text: str) -> str:
    """Convert markdown formatting to valid ReportLab XML tags."""
    if not text:
        return ""
    escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    parts = escaped.split("**")
    res = []
    for i, part in enumerate(parts):
        if i % 2 == 1:
            res.append(f"<b>{part}</b>")
        else:
            res.append(part)
    return "".join(res)


def generate_pdf_report(req: ExportRequest) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "PDFTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1b4332"),
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "PDFSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#2d6a4f"),
        spaceAfter=12,
    )
    heading_style = ParagraphStyle(
        "PDFHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#1b4332"),
        spaceBefore=10,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "PDFBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=6,
    )

    elements = []

    # Title Banner
    is_summary = req.mode == "summary"
    doc_title = (req.title or ("MRPL Executive Summary" if is_summary else "MRPL Operational Report")).upper()
    elements.append(Paragraph(doc_title, title_style))
    elements.append(Paragraph("MRPL SOVEREIGN AI WORKBENCH • AIR-GAPPED KNOWLEDGE BASE", subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#1b4332"), spaceAfter=12))

    # Mode Indicator Badge
    mode_str = "EXECUTIVE SUMMARY REPORT" if is_summary else "DETAILED OPERATIONAL ANALYSIS REPORT"
    elements.append(Paragraph(f"<b>Report Type:</b> {mode_str} | <b>Date:</b> {datetime.now().strftime('%d %b %Y, %H:%M UTC')}", body_style))
    elements.append(Spacer(1, 10))

    # Parse Sections & Content Lines
    lines = req.content.split("\n")
    for line in lines:
        line_str = line.strip()
        if not line_str:
            continue
        if line_str.startswith("#"):
            clean_hdr = markdown_to_pdf_xml(clean_markdown_headers(line_str))
            elements.append(Paragraph(clean_hdr, heading_style))
        elif line_str.startswith("- ") or line_str.startswith("* "):
            bullet_txt = "• " + markdown_to_pdf_xml(clean_markdown_headers(line_str[2:]))
            elements.append(Paragraph(bullet_txt, body_style))
        else:
            clean_p = markdown_to_pdf_xml(line_str)
            elements.append(Paragraph(clean_p, body_style))

    # Add Sources Table
    if req.sources:
        elements.append(Spacer(1, 14))
        elements.append(Paragraph("Verified Knowledge Base Sources & Citations", heading_style))
        
        table_data = [["Source Title", "Category", "Metadata", "Trust Status"]]
        for s in req.sources:
            table_data.append([
                s.get("title", "MRPL Document"),
                s.get("category", "Knowledge Base"),
                s.get("meta", "v1.0"),
                s.get("badge", "Verified"),
            ])

        t = Table(table_data, colWidths=[200, 100, 140, 100])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1b4332")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 8.5),
        ]))
        elements.append(t)

    # Footer Notice
    elements.append(Spacer(1, 14))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=6))
    elements.append(Paragraph("<font size=7 color='#64748b'>Confidential • MRPL Enterprise Sovereign Workbench • Generated from verified refinery records.</font>", body_style))

    doc.build(elements)
    return buffer.getvalue()


def generate_docx_report(req: ExportRequest) -> bytes:
    doc = docx.Document()
    
    # Page Margins
    sections = doc.sections
    for s in sections:
        s.top_margin = Inches(0.75)
        s.bottom_margin = Inches(0.75)
        s.left_margin = Inches(0.75)
        s.right_margin = Inches(0.75)

    is_summary = req.mode == "summary"
    title_text = req.title or ("MRPL Executive Summary" if is_summary else "MRPL Operational Report")

    # Title Header
    p_title = doc.add_paragraph()
    run_title = p_title.add_run(title_text.upper())
    run_title.font.name = "Arial"
    run_title.font.size = Pt(20)
    run_title.font.bold = True
    run_title.font.color.rgb = RGBColor(27, 67, 50)  # #1b4332

    p_sub = doc.add_paragraph()
    run_sub = p_sub.add_run("MRPL SOVEREIGN AI WORKBENCH • AIR-GAPPED KNOWLEDGE BASE")
    run_sub.font.name = "Arial"
    run_sub.font.size = Pt(9.5)
    run_sub.font.bold = True
    run_sub.font.color.rgb = RGBColor(45, 106, 79)

    p_meta = doc.add_paragraph()
    mode_str = "Executive Summary Report" if is_summary else "Detailed Operational Analysis"
    run_meta = p_meta.add_run(f"Report Type: {mode_str}  |  Generated: {datetime.now().strftime('%d %b %Y, %H:%M UTC')}")
    run_meta.font.name = "Arial"
    run_meta.font.size = Pt(9)
    run_meta.font.italic = True
    run_meta.font.color.rgb = RGBColor(100, 116, 139)

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # Content Processing
    lines = req.content.split("\n")
    for line in lines:
        line_str = line.strip()
        if not line_str:
            continue
        if line_str.startswith("#"):
            hdr_text = clean_markdown_headers(line_str)
            p_hdr = doc.add_paragraph()
            r_hdr = p_hdr.add_run(hdr_text)
            r_hdr.font.name = "Arial"
            r_hdr.font.size = Pt(13)
            r_hdr.font.bold = True
            r_hdr.font.color.rgb = RGBColor(27, 67, 50)
            p_hdr.paragraph_format.space_before = Pt(8)
            p_hdr.paragraph_format.space_after = Pt(3)
        elif line_str.startswith("- ") or line_str.startswith("* "):
            bullet_txt = clean_markdown_headers(line_str[2:])
            p_b = doc.add_paragraph(style="List Bullet")
            r_b = p_b.add_run(bullet_txt)
            r_b.font.name = "Arial"
            r_b.font.size = Pt(10)
        else:
            p_txt = doc.add_paragraph()
            clean_txt = clean_markdown_headers(line_str)
            r_txt = p_txt.add_run(clean_txt)
            r_txt.font.name = "Arial"
            r_txt.font.size = Pt(10)
            r_txt.font.color.rgb = RGBColor(30, 41, 59)

    # Sources Table
    if req.sources:
        doc.add_paragraph().paragraph_format.space_before = Pt(12)
        p_shdr = doc.add_paragraph()
        r_shdr = p_shdr.add_run("Verified Knowledge Base Sources & Citations")
        r_shdr.font.name = "Arial"
        r_shdr.font.size = Pt(12)
        r_shdr.font.bold = True
        r_shdr.font.color.rgb = RGBColor(27, 67, 50)

        table = doc.add_table(rows=1, cols=4)
        hdr_cells = table.rows[0].cells
        headers = ["Source Title", "Category", "Metadata", "Trust Status"]
        for i, h in enumerate(headers):
            hdr_cells[i].text = h
            hdr_cells[i].paragraphs[0].runs[0].font.bold = True
            hdr_cells[i].paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)

        for s in req.sources:
            row_cells = table.add_row().cells
            row_cells[0].text = str(s.get("title", "MRPL Document"))
            row_cells[1].text = str(s.get("category", "Knowledge Base"))
            row_cells[2].text = str(s.get("meta", "v1.0"))
            row_cells[3].text = str(s.get("badge", "Verified"))

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def generate_pptx_report(req: ExportRequest) -> bytes:
    prs = pptx.Presentation()
    prs.slide_width = PptxInches(10)
    prs.slide_height = PptxInches(5.625)  # 16:9 widescreen layout

    blank_layout = prs.slide_layouts[6]
    is_summary = req.mode == "summary"

    # Slide 1: Title Slide (Dark Green MRPL Branding)
    slide1 = prs.slides.add_slide(blank_layout)
    bg1 = slide1.shapes.add_shape(pptx.enum.shapes.MSO_SHAPE.RECTANGLE, 0, 0, PptxInches(10), PptxInches(5.625))
    bg1.fill.solid()
    bg1.fill.fore_color.rgb = PptxRGBColor(27, 67, 50)  # Dark Green
    bg1.line.color.rgb = PptxRGBColor(27, 67, 50)

    txBox1 = slide1.shapes.add_textbox(PptxInches(0.8), PptxInches(1.5), PptxInches(8.4), PptxInches(2.5))
    tf1 = txBox1.text_frame
    tf1.word_wrap = True

    p1 = tf1.paragraphs[0]
    p1.text = (req.title or ("MRPL Executive Summary" if is_summary else "MRPL Operational Presentation")).upper()
    p1.font.size = PptxPt(26)
    p1.font.bold = True
    p1.font.color.rgb = PptxRGBColor(255, 255, 255)

    p2 = tf1.add_paragraph()
    p2.text = "MRPL SOVEREIGN AI WORKBENCH • AIR-GAPPED KNOWLEDGE BASE"
    p2.font.size = PptxPt(13)
    p2.font.color.rgb = PptxRGBColor(167, 243, 208)

    p3 = tf1.add_paragraph()
    mode_str = "Executive Summary" if is_summary else "Detailed Analysis"
    p3.text = f"Report Format: {mode_str} | Date: {datetime.now().strftime('%d %b %Y')}"
    p3.font.size = PptxPt(11)
    p3.font.color.rgb = PptxRGBColor(203, 213, 225)

    # Parse content into slides
    lines = [clean_markdown_headers(l) for l in req.content.split("\n") if l.strip()]
    content_chunks = [lines[i:i+6] for i in range(0, len(lines), 6)]

    for idx, chunk in enumerate(content_chunks, start=2):
        slide = prs.slides.add_slide(blank_layout)
        
        # Header bar
        header_box = slide.shapes.add_textbox(PptxInches(0.6), PptxInches(0.4), PptxInches(8.8), PptxInches(0.6))
        tf_h = header_box.text_frame
        p_h = tf_h.paragraphs[0]
        p_h.text = f"Slide {idx - 1}: {req.title or 'Operational Analysis'}"
        p_h.font.size = PptxPt(18)
        p_h.font.bold = True
        p_h.font.color.rgb = PptxRGBColor(27, 67, 50)

        # Content Box
        body_box = slide.shapes.add_textbox(PptxInches(0.6), PptxInches(1.2), PptxInches(8.8), PptxInches(3.8))
        tf_b = body_box.text_frame
        tf_b.word_wrap = True

        for line_item in chunk:
            p_b = tf_b.add_paragraph()
            p_b.text = "• " + line_item if not line_item.startswith("•") else line_item
            p_b.font.size = PptxPt(13)
            p_b.font.color.rgb = PptxRGBColor(30, 41, 59)
            p_b.space_after = PptxPt(6)

    # Slide N: Sources Slide
    if req.sources:
        slide_src = prs.slides.add_slide(blank_layout)
        header_box = slide_src.shapes.add_textbox(PptxInches(0.6), PptxInches(0.4), PptxInches(8.8), PptxInches(0.6))
        p_h = header_box.text_frame.paragraphs[0]
        p_h.text = "Verified Knowledge Base Sources"
        p_h.font.size = PptxPt(18)
        p_h.font.bold = True
        p_h.font.color.rgb = PptxRGBColor(27, 67, 50)

        body_box = slide_src.shapes.add_textbox(PptxInches(0.6), PptxInches(1.2), PptxInches(8.8), PptxInches(3.8))
        tf_s = body_box.text_frame
        tf_s.word_wrap = True

        for s in req.sources:
            p_s = tf_s.add_paragraph()
            title = s.get("title", "MRPL Document")
            meta = s.get("meta", "v1.0")
            badge = s.get("badge", "Verified")
            p_s.text = f"📄 {title} — ({meta}) [{badge}]"
            p_s.font.size = PptxPt(13)
            p_s.font.color.rgb = PptxRGBColor(45, 106, 79)
            p_s.space_after = PptxPt(8)

    buffer = io.BytesIO()
    prs.save(buffer)
    return buffer.getvalue()


@router.post("/document")
async def export_document(req: ExportRequest):
    """
    Export assistant response into downloadable PDF, DOCX, or PPTX format.
    """
    if req.mode == "summary":
        req.content = format_as_executive_summary(req.content)

    fmt = req.format.lower().strip()
    if fmt == "pdf":
        file_bytes = generate_pdf_report(req)
        media_type = "application/pdf"
        ext = "pdf"
    elif fmt == "docx":
        file_bytes = generate_docx_report(req)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ext = "docx"
    elif fmt == "pptx":
        file_bytes = generate_pptx_report(req)
        media_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        ext = "pptx"
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format '{fmt}'. Choose pdf, docx, or pptx.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = "MRPL_Summary" if req.mode == "summary" else "MRPL_Report"
    filename = f"{prefix}_{timestamp}.{ext}"

    return Response(
        content=file_bytes,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": media_type,
        },
    )

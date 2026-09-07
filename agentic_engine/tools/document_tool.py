from __future__ import annotations

from typing import Any, Dict, Optional
from .base import BaseTool
from ..document_output import DocumentOutput


class DocumentExporterTool(BaseTool):
    """Traceable exporter for PDF, XLSX, DOCX, and CSV files."""
    name = "document_exporter"
    description = "Renders structured text, markdown, and tables into formal files (PDF, XLSX, DOCX, CSV)."

    def __init__(self, doc_output: Optional[DocumentOutput] = None):
        self.doc_output = doc_output or DocumentOutput()

    def _execute(self, filename: str, content: str, format_type: str = "xlsx", fmt: str = "", **kwargs) -> Dict[str, Any]:
        target_fmt = fmt or format_type
        file_path = self.doc_output.create(filename=filename, content=content, fmt=target_fmt)
        return {
            "format": target_fmt,
            "file_path": file_path,
        }

"""
ReportTool for Main AI Agent wrapping ReportLab executive PDF generation.
Compiles verified structured content into executive PDF artifacts.
"""

import logging
from typing import Any, Dict, Optional
from agent.tools.base import BaseTool
from agent.pdf_generator import ReportLabPDFGenerator
from agent.models.schemas import ArtifactMetadata, StructuredPDFContent

logger = logging.getLogger("agent.tools.report_tool")


class ReportTool(BaseTool):
    """Capability Tool for generating executive SOP and summary PDF artifacts."""

    def __init__(self, pdf_generator: Optional[ReportLabPDFGenerator] = None):
        self.pdf_generator = pdf_generator or ReportLabPDFGenerator()

    @property
    def name(self) -> str:
        return "generate_report_pdf"

    @property
    def description(self) -> str:
        return "Generate executive ReportLab PDF SOP document from verified structured content."

    def execute(self, **kwargs) -> ArtifactMetadata:
        content = kwargs.get("content")
        task_id = kwargs.get("task_id", "global")

        if isinstance(content, dict):
            content = StructuredPDFContent.model_validate(content)

        if not isinstance(content, StructuredPDFContent):
            raise ValueError("ReportTool requires valid StructuredPDFContent input.")

        pdf_bytes, filename = self.pdf_generator.generate_sop_pdf(
            content=content,
            task_id=task_id,
        )

        try:
            from rag.storage.minio_storage import minio_client
            storage_uri = minio_client.save_file(
                file_id=task_id,
                content_bytes=pdf_bytes,
                filename=filename,
            )
        except Exception as ex:
            logger.warning(f"MinIO storage save failed ({ex}). Falling back to LocalObjectStorage.")
            from rag.storage.object_storage import LocalObjectStorage
            local_store = LocalObjectStorage()
            storage_uri = local_store.save_file(
                file_id=task_id,
                content_bytes=pdf_bytes,
                filename=filename,
            )

        return ArtifactMetadata(
            filename=filename,
            content_type="application/pdf",
            storage_uri=storage_uri,
            file_size_bytes=len(pdf_bytes),
            bucket="trusted",
        )

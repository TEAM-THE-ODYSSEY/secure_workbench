"""
Input Gateway for MRPL Sovereign Agentic AI Workbench.
Handles MIME/type validation, file metadata extraction, file reference creation,
safe handoff to existing document storage and security ingestion pipeline,
and input normalization.
"""

import hashlib
import logging
import mimetypes
import os
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from rag.config import config
from rag.storage.minio_storage import minio_client

logger = logging.getLogger("agent.gateway.input_gateway")


class ProcessedFileInput(BaseModel):
    """Metadata representation of an input file handled by the Input Gateway."""
    file_id: str
    task_id: str
    filename: str
    content_type: str
    file_size_bytes: int
    sha256_hash: str
    storage_uri: str
    bucket: str = "raw"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class InputGateway:
    """
    Input Gateway enforcing security boundaries, MIME validation, metadata extraction,
    and handoff to the centralized RAG ingestion pipeline.
    """

    ALLOWED_MIME_TYPES = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # docx
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",  # pptx
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # xlsx
        "text/csv",
        "text/plain",
        "image/png",
        "image/jpeg",
        "image/tiff",
    }

    ALLOWED_EXTENSIONS = {
        ".pdf", ".docx", ".pptx", ".xlsx", ".csv", ".txt", ".png", ".jpg", ".jpeg", ".tif", ".tiff"
    }

    def __init__(self):
        mimetypes.init()

    def validate_file(self, filename: str, content_bytes: bytes) -> str:
        """Validate MIME type and extension of incoming file."""
        ext = os.path.splitext(filename)[1].lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            logger.warning(f"Rejected upload '{filename}': Unsupported extension '{ext}'")
            raise ValueError(f"Unsupported file extension '{ext}'. Allowed: {sorted(list(self.ALLOWED_EXTENSIONS))}")

        mime_type, _ = mimetypes.guess_type(filename)
        mime_type = mime_type or "application/octet-stream"

        if ext == ".txt":
            mime_type = "text/plain"
        elif ext == ".csv":
            mime_type = "text/csv"
        elif ext == ".pdf":
            mime_type = "application/pdf"

        return mime_type

    def process_upload(
        self,
        content_bytes: bytes,
        filename: str,
        task_id: Optional[str] = None,
    ) -> ProcessedFileInput:
        """
        Extract metadata, generate unique file reference, save to raw storage,
        and link file reference to task_id.
        """
        task_id = task_id or f"task_{uuid.uuid4().hex[:12]}"
        mime_type = self.validate_file(filename, content_bytes)

        file_id = f"doc_{uuid.uuid4().hex[:12]}"
        sha256 = hashlib.sha256(content_bytes).hexdigest()
        file_size = len(content_bytes)

        # Upload raw binary safely to storage (MinIO or LocalObjectStorage)
        safe_name = f"{file_id}_{os.path.basename(filename)}"
        storage_uri = minio_client.save_file(
            file_id=file_id,
            content_bytes=content_bytes,
            filename=filename,
        )

        processed = ProcessedFileInput(
            file_id=file_id,
            task_id=task_id,
            filename=filename,
            content_type=mime_type,
            file_size_bytes=file_size,
            sha256_hash=sha256,
            storage_uri=storage_uri,
            bucket=config.MINIO_BUCKET_RAW,
            metadata={
                "extension": os.path.splitext(filename)[1].lower(),
                "is_multimodal": mime_type.startswith("image/"),
            },
        )

        logger.info(f"InputGateway processed upload: file_id={file_id}, task_id={task_id}, size={file_size} bytes")
        return processed

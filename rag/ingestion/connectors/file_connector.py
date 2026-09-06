"""
File connector for loading documents from local and network filesystem locations.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import hashlib
import logging
import os
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class RawIngestedDocument(BaseModel):
    """Data model representing a raw document ingested from a source."""
    source_id: str
    filename: str
    filepath: str
    content_bytes: bytes
    extension: str
    file_size_bytes: int
    modified_at: datetime
    checksum: str
    raw_metadata: Dict[str, str] = Field(default_factory=dict)


class BaseConnector(ABC):
    """Abstract interface for all ingestion connectors."""

    @abstractmethod
    def fetch_documents(self) -> List[RawIngestedDocument]:
        """Fetch all documents from the source."""
        pass

    @abstractmethod
    def fetch_single(self, identifier: str) -> Optional[RawIngestedDocument]:
        """Fetch a specific document by identifier."""
        pass


class FileConnector(BaseConnector):
    """Connector for reading documents from local or mounted shared directory paths."""

    def __init__(self, target_path: str, allowed_extensions: Optional[List[str]] = None):
        self.target_path = target_path
        self.allowed_extensions = [
            ext.lower() if ext.startswith(".") else f".{ext.lower()}"
            for ext in (allowed_extensions or [".pdf", ".docx", ".xlsx", ".xls", ".txt", ".csv"])
        ]

    def _compute_checksum(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def fetch_single(self, identifier: str) -> Optional[RawIngestedDocument]:
        """Fetch a single file by absolute or relative filepath."""
        filepath = os.path.abspath(identifier)
        if not os.path.exists(filepath) or not os.path.isfile(filepath):
            logger.warning(f"File not found: {filepath}")
            return None

        ext = os.path.splitext(filepath)[1].lower()
        if self.allowed_extensions and ext not in self.allowed_extensions:
            logger.info(f"Skipping file {filepath} with unsupported extension {ext}")
            return None

        try:
            with open(filepath, "rb") as f:
                content = f.read()
            
            stat = os.stat(filepath)
            modified_at = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
            checksum = self._compute_checksum(content)

            return RawIngestedDocument(
                source_id=f"file:{filepath}",
                filename=os.path.basename(filepath),
                filepath=filepath,
                content_bytes=content,
                extension=ext,
                file_size_bytes=len(content),
                modified_at=modified_at,
                checksum=checksum,
                raw_metadata={
                    "connector": "FileConnector",
                    "absolute_path": filepath,
                }
            )
        except Exception as e:
            logger.error(f"Failed to read file {filepath}: {e}", exc_info=True)
            return None

    def fetch_documents(self) -> List[RawIngestedDocument]:
        """Recursively scan directory target_path for matching files."""
        documents: List[RawIngestedDocument] = []
        if not os.path.exists(self.target_path):
            logger.warning(f"Target path does not exist: {self.target_path}")
            return documents

        if os.path.isfile(self.target_path):
            doc = self.fetch_single(self.target_path)
            if doc:
                documents.append(doc)
            return documents

        for root, _, files in os.walk(self.target_path):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in self.allowed_extensions:
                    full_path = os.path.join(root, file)
                    doc = self.fetch_single(full_path)
                    if doc:
                        documents.append(doc)

        logger.info(f"FileConnector fetched {len(documents)} document(s) from {self.target_path}")
        return documents

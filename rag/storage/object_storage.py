"""
Object storage abstraction for persisting original raw document files and binaries.
"""

from abc import ABC, abstractmethod
import logging
import os
from typing import Optional
from rag.config import config

logger = logging.getLogger(__name__)


class ObjectStorage(ABC):
    """Abstract interface for raw document binary storage."""

    @abstractmethod
    def save_file(self, file_id: str, content_bytes: bytes, filename: str) -> str:
        """Save document bytes and return storage path / URI."""
        pass

    @abstractmethod
    def get_file(self, file_id: str) -> Optional[bytes]:
        """Retrieve raw document bytes by file_id."""
        pass

    @abstractmethod
    def delete_file(self, file_id: str) -> bool:
        """Delete raw document from storage."""
        pass


class LocalObjectStorage(ObjectStorage):
    """Local filesystem implementation of ObjectStorage."""

    def __init__(self, storage_dir: str = config.OBJECT_STORAGE_DIR):
        self.storage_dir = os.path.abspath(storage_dir)
        os.makedirs(self.storage_dir, exist_ok=True)

    def save_file(self, file_id: str, content_bytes: bytes, filename: str) -> str:
        safe_filename = f"{file_id}_{os.path.basename(filename)}"
        filepath = os.path.join(self.storage_dir, safe_filename)
        try:
            with open(filepath, "wb") as f:
                f.write(content_bytes)
            logger.info(f"LocalObjectStorage saved file {safe_filename} ({len(content_bytes)} bytes)")
            return filepath
        except Exception as e:
            logger.error(f"Failed to save file to object storage: {e}", exc_info=True)
            raise e

    def get_file(self, file_id: str) -> Optional[bytes]:
        for fname in os.listdir(self.storage_dir):
            if fname.startswith(file_id):
                fpath = os.path.join(self.storage_dir, fname)
                with open(fpath, "rb") as f:
                    return f.read()
        return None

    def delete_file(self, file_id: str) -> bool:
        for fname in os.listdir(self.storage_dir):
            if fname.startswith(file_id):
                fpath = os.path.join(self.storage_dir, fname)
                os.remove(fpath)
                return True
        return False

    def upload_raw_document(
        self,
        file_bytes: bytes,
        filename: str,
        document_id: str,
        bucket_name: str = "raw",
    ) -> str:
        """Helper method saving file to bucket subfolder and returning URI."""
        bucket_dir = os.path.join(self.storage_dir, bucket_name)
        os.makedirs(bucket_dir, exist_ok=True)
        safe_filename = f"{document_id}_{os.path.basename(filename)}"
        filepath = os.path.join(bucket_dir, safe_filename)
        with open(filepath, "wb") as f:
            f.write(file_bytes)
        return f"file://{filepath}"


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
    def get_file(self, object_name: str, bucket: Optional[str] = None) -> Optional[bytes]:
        """Retrieve raw document bytes by object_name or file_id."""
        pass

    @abstractmethod
    def delete_file(self, object_name: str, bucket: Optional[str] = None) -> bool:
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

    def get_file(self, object_name: str, bucket: Optional[str] = None) -> Optional[bytes]:
        search_dirs = []
        if bucket:
            search_dirs.append(os.path.join(self.storage_dir, bucket))
        search_dirs.append(self.storage_dir)

        base_query = object_name[:-4] if object_name.endswith(".pdf") else object_name

        for d in search_dirs:
            if not os.path.exists(d):
                continue
            for fname in os.listdir(d):
                if fname == object_name or fname.startswith(base_query) or base_query in fname:
                    fpath = os.path.join(d, fname)
                    if os.path.isfile(fpath):
                        with open(fpath, "rb") as f:
                            return f.read()

        for root, _, files in os.walk(self.storage_dir):
            for fname in files:
                if fname == object_name or fname.startswith(base_query) or base_query in fname:
                    fpath = os.path.join(root, fname)
                    if os.path.isfile(fpath):
                        with open(fpath, "rb") as f:
                            return f.read()
        return None

    def delete_file(self, object_name: str, bucket: Optional[str] = None) -> bool:
        for root, _, files in os.walk(self.storage_dir):
            for fname in files:
                if fname == object_name or fname.startswith(object_name) or object_name in fname:
                    fpath = os.path.join(root, fname)
                    if os.path.isfile(fpath):
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


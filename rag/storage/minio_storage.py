"""
MinIO-based object storage for secure document persistence.
Implements the ObjectStorage ABC with separate buckets for raw, trusted, and quarantined documents.
Falls back to LocalObjectStorage when MinIO is not available.
"""

import io
import logging
from typing import Optional

from rag.config import config
from rag.storage.object_storage import ObjectStorage

logger = logging.getLogger(__name__)


class MinIOObjectStorage(ObjectStorage):
    """
    Object storage implementation using MinIO.
    Documents are organized into buckets by trust status:
      - raw: Newly uploaded, unprocessed files
      - trusted: Documents that passed security pipeline
      - quarantine: Documents flagged by security pipeline
    """

    def __init__(
        self,
        endpoint: str = config.MINIO_ENDPOINT,
        access_key: str = config.MINIO_ACCESS_KEY,
        secret_key: str = config.MINIO_SECRET_KEY,
        secure: bool = config.MINIO_SECURE,
    ):
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.secure = secure
        self._client = None

    def _get_client(self):
        """Lazily initialize MinIO client."""
        if self._client is None:
            try:
                from minio import Minio
                self._client = Minio(
                    self.endpoint,
                    access_key=self.access_key,
                    secret_key=self.secret_key,
                    secure=self.secure,
                )
                # Ensure required buckets exist
                for bucket_name in [
                    config.MINIO_BUCKET_RAW,
                    config.MINIO_BUCKET_TRUSTED,
                    config.MINIO_BUCKET_QUARANTINE,
                ]:
                    if not self._client.bucket_exists(bucket_name):
                        self._client.make_bucket(bucket_name)
                        logger.info(f"Created MinIO bucket: {bucket_name}")
            except ImportError:
                raise ImportError("minio package is required. Install with: pip install minio")
            except Exception as e:
                logger.error(f"Failed to initialize MinIO client: {e}")
                raise
        return self._client

    def save_file(
        self,
        file_id: Optional[str] = None,
        content_bytes: Optional[bytes] = None,
        filename: Optional[str] = None,
        file_bytes: Optional[bytes] = None,
        object_name: Optional[str] = None,
        bucket: Optional[str] = None,
    ) -> str:
        """Save file bytes to MinIO bucket. Returns the object URI."""
        data = file_bytes if file_bytes is not None else content_bytes
        if data is None:
            raise ValueError("file_bytes or content_bytes must be provided")

        obj_name = object_name or file_id or (filename if filename else "document")
        bucket = bucket or config.MINIO_BUCKET_RAW
        client = self._get_client()

        data_stream = io.BytesIO(data)
        client.put_object(
            bucket_name=bucket,
            object_name=obj_name,
            data=data_stream,
            length=len(data),
        )
        uri = f"minio://{bucket}/{obj_name}"
        logger.info(f"Saved {len(data)} bytes to {uri}")
        return uri

    def get_file(self, object_name: str, bucket: Optional[str] = None) -> Optional[bytes]:
        """Retrieve file bytes from MinIO bucket."""
        bucket = bucket or config.MINIO_BUCKET_RAW
        try:
            client = self._get_client()
            response = client.get_object(bucket_name=bucket, object_name=object_name)
            try:
                data = response.read()
                return data
            finally:
                response.close()
                response.release_conn()
        except Exception as e:
            logger.warning(f"File '{object_name}' not found or error accessing bucket '{bucket}': {e}")
            return None

    def delete_file(self, object_name: str, bucket: Optional[str] = None) -> None:
        """Delete file from MinIO bucket."""
        bucket = bucket or config.MINIO_BUCKET_RAW
        client = self._get_client()
        client.remove_object(bucket_name=bucket, object_name=object_name)
        logger.info(f"Deleted minio://{bucket}/{object_name}")

    def move_to_bucket(
        self,
        object_name: str,
        from_bucket: str,
        to_bucket: str,
    ) -> str:
        """Move an object between buckets (copy + delete)."""
        from minio.commonconfig import CopySource

        client = self._get_client()
        copy_source = CopySource(from_bucket, object_name)
        client.copy_object(to_bucket, object_name, copy_source)
        client.remove_object(from_bucket, object_name)
        new_uri = f"minio://{to_bucket}/{object_name}"
        logger.info(f"Moved {object_name} from {from_bucket} to {to_bucket}")
        return new_uri

    def file_exists(self, object_name: str, bucket: Optional[str] = None) -> bool:
        """Check if a file exists in the bucket."""
        bucket = bucket or config.MINIO_BUCKET_RAW
        client = self._get_client()
        try:
            client.stat_object(bucket_name=bucket, object_name=object_name)
            return True
        except Exception:
            return False


    def upload_raw_document(
        self,
        file_bytes: bytes,
        filename: str,
        document_id: str,
        bucket_name: str = "raw",
    ) -> str:
        """Upload raw document bytes to specified MinIO bucket."""
        object_name = f"{document_id}_{filename}"
        return self.save_file(
            file_bytes=file_bytes,
            object_name=object_name,
            bucket=bucket_name,
        )


def get_object_storage() -> ObjectStorage:
    """Factory: returns MinIO storage if enabled, else LocalObjectStorage fallback."""
    if config.MINIO_ENABLED:
        try:
            storage = MinIOObjectStorage()
            storage._get_client()  # Test connection
            return storage
        except Exception as e:
            logger.warning(f"MinIO unavailable ({e}), falling back to local filesystem storage.")

    from rag.storage.object_storage import LocalObjectStorage
    return LocalObjectStorage(storage_dir=config.OBJECT_STORAGE_DIR)


# Global singleton instance for storage operations
minio_client: ObjectStorage = get_object_storage()


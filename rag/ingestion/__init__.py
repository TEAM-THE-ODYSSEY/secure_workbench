"""
Ingestion module for fetching, watching, and queueing documents.
"""

from rag.ingestion.connectors.file_connector import FileConnector, RawIngestedDocument
from rag.ingestion.connectors.api_connector import APIConnector
from rag.ingestion.connectors.database_connector import DatabaseConnector
from rag.ingestion.watcher import DocumentWatcher
from rag.ingestion.change_detector import ChangeDetector, DocumentChangeState
from rag.ingestion.queue import IngestionQueue

__all__ = [
    "FileConnector",
    "RawIngestedDocument",
    "APIConnector",
    "DatabaseConnector",
    "DocumentWatcher",
    "ChangeDetector",
    "DocumentChangeState",
    "IngestionQueue",
]

"""
Queue abstraction for asynchronous document ingestion and processing.
"""

from abc import ABC, abstractmethod
import queue
import logging
from typing import Optional, Any
from rag.ingestion.connectors.file_connector import RawIngestedDocument

logger = logging.getLogger(__name__)


class BaseIngestionQueue(ABC):
    """Abstract interface for ingestion queuing implementations."""

    @abstractmethod
    def enqueue(self, document: RawIngestedDocument) -> bool:
        """Enqueue document for pipeline processing."""
        pass

    @abstractmethod
    def dequeue(self, block: bool = True, timeout: Optional[float] = None) -> Optional[RawIngestedDocument]:
        """Dequeue next document for processing."""
        pass

    @abstractmethod
    def size(self) -> int:
        """Return current size of queue."""
        pass


class InMemoryIngestionQueue(BaseIngestionQueue):
    """In-memory thread-safe queue implementation for standalone or testing setups."""

    def __init__(self, maxsize: int = 1000):
        self._queue: queue.Queue = queue.Queue(maxsize=maxsize)

    def enqueue(self, document: RawIngestedDocument) -> bool:
        try:
            self._queue.put(document, block=False)
            logger.debug(f"Enqueued document {document.filename} (Queue size: {self.size()})")
            return True
        except queue.Full:
            logger.error(f"Ingestion queue is full. Failed to enqueue {document.filename}")
            return False

    def dequeue(self, block: bool = True, timeout: Optional[float] = None) -> Optional[RawIngestedDocument]:
        try:
            doc = self._queue.get(block=block, timeout=timeout)
            logger.debug(f"Dequeued document {doc.filename}")
            return doc
        except queue.Empty:
            return None

    def size(self) -> int:
        return self._queue.qsize()


class IngestionQueue(InMemoryIngestionQueue):
    """Default IngestionQueue reference."""
    pass

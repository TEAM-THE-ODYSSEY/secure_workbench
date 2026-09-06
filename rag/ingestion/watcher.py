"""
Document watcher component for polling filesystem locations and notifying pipeline of document changes.
"""

import logging
import time
from typing import Callable, List, Optional
from rag.ingestion.connectors.file_connector import FileConnector, RawIngestedDocument
from rag.ingestion.change_detector import ChangeDetector, DocumentChangeState

logger = logging.getLogger(__name__)


class DocumentWatcher:
    """Monitors configured connectors or target directories for document additions/modifications."""

    def __init__(self, connector: FileConnector, change_detector: Optional[ChangeDetector] = None):
        self.connector = connector
        self.change_detector = change_detector or ChangeDetector()

    def scan_for_changes(self) -> List[RawIngestedDocument]:
        """Perform a single scan and return documents that are NEW or MODIFIED."""
        all_docs = self.connector.fetch_documents()
        changed_docs: List[RawIngestedDocument] = []

        for doc in all_docs:
            result = self.change_detector.detect_change(doc.source_id, doc.checksum)
            if result.state in (DocumentChangeState.NEW, DocumentChangeState.MODIFIED):
                logger.info(f"Detected {result.state.value} document: {doc.filename} ({doc.source_id})")
                changed_docs.append(doc)
            else:
                logger.debug(f"Document {doc.filename} is UNCHANGED. Skipping.")

        return changed_docs

    def start_polling(self, callback: Callable[[RawIngestedDocument], None], interval_seconds: int = 5, max_loops: Optional[int] = None) -> None:
        """Poll directory periodically and invoke callback for changed documents."""
        logger.info(f"Starting DocumentWatcher polling on {self.connector.target_path} (interval={interval_seconds}s)")
        loop_count = 0
        try:
            while max_loops is None or loop_count < max_loops:
                changed = self.scan_for_changes()
                for doc in changed:
                    callback(doc)
                    self.change_detector.mark_indexed(doc.source_id, doc.checksum)
                
                loop_count += 1
                if max_loops is not None and loop_count >= max_loops:
                    break
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            logger.info("DocumentWatcher polling stopped by user.")

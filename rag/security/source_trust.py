import logging
from rag.storage.postgres import SourceType, TrustLevel

logger = logging.getLogger(__name__)

class SourceTrustManager:
    """Evaluates source trust based on SourceType and history."""

    def evaluate_source(self, source_type: SourceType) -> TrustLevel:
        logger.info(f"Evaluating trust for source type: {source_type}")
        if source_type in [SourceType.ADMIN_UPLOAD, SourceType.FILE_SYSTEM]:
            return TrustLevel.TRUSTED
        elif source_type in [SourceType.SQL_DATABASE, SourceType.EVENT_SOURCE]:
            return TrustLevel.VERIFIED
        else:
            return TrustLevel.UNTRUSTED

"""
CSV document loader using pandas for structured text representation.
"""

import io
import logging
from typing import Any, Dict, List

from rag.processing.loaders.pdf_loader import BaseLoader, LoadedDocument, LoadedPage

logger = logging.getLogger(__name__)

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


class CSVLoader(BaseLoader):
    """Loader for CSV files, converting rows to structured text blocks."""

    def load(self, content_bytes: bytes, filename: str) -> LoadedDocument:
        pages: List[LoadedPage] = []
        doc_metadata: Dict[str, Any] = {}

        if not PANDAS_AVAILABLE:
            logger.error("pandas is not installed. Returning empty document.")
            return LoadedDocument(
                filename=filename,
                extension=".csv",
                total_pages=1,
                pages=[LoadedPage(page_number=1, text="", metadata={"error": "pandas not installed"})],
                document_metadata=doc_metadata,
            )

        try:
            df = pd.read_csv(io.BytesIO(content_bytes))
            
            # Convert to markdown table format or structured text
            text = df.to_markdown(index=False)
            
            pages.append(
                LoadedPage(
                    page_number=1,
                    text=text,
                    metadata={"rows": len(df), "columns": len(df.columns)},
                )
            )

            logger.info(f"CSVLoader successfully loaded {filename} ({len(df)} rows)")
        except Exception as e:
            logger.error(f"Error loading CSV {filename}: {e}", exc_info=True)
            pages = [LoadedPage(page_number=1, text="", metadata={"error": str(e)})]

        return LoadedDocument(
            filename=filename,
            extension=".csv",
            total_pages=1,
            pages=pages,
            document_metadata=doc_metadata,
        )

"""
Excel document loader using openpyxl for spreadsheets, worksheets, and tabular data extraction.
"""

import io
import logging
from typing import Any, Dict, List
import openpyxl

from rag.processing.loaders.pdf_loader import BaseLoader, LoadedDocument, LoadedPage

logger = logging.getLogger(__name__)


class ExcelLoader(BaseLoader):
    """Loader for Microsoft Excel (.xlsx, .xls) spreadsheets."""

    def load(self, content_bytes: bytes, filename: str) -> LoadedDocument:
        pages: List[LoadedPage] = []
        doc_metadata: Dict[str, Any] = {}

        try:
            stream = io.BytesIO(content_bytes)
            wb = openpyxl.load_workbook(stream, data_only=True)
            doc_metadata["sheet_names"] = wb.sheetnames

            for page_idx, sheet_name in enumerate(wb.sheetnames, start=1):
                sheet = wb[sheet_name]
                rows_text: List[str] = []
                
                rows_text.append(f"Worksheet: {sheet_name}")

                for row in sheet.iter_rows(values_only=True):
                    # Filter empty rows
                    if any(cell is not None for cell in row):
                        cell_strings = [str(cell).strip() if cell is not None else "" for cell in row]
                        rows_text.append("| " + " | ".join(cell_strings) + " |")

                sheet_text = "\n".join(rows_text)
                pages.append(
                    LoadedPage(
                        page_number=page_idx,
                        text=sheet_text,
                        metadata={"sheet_name": sheet_name, "max_row": sheet.max_row, "max_column": sheet.max_column},
                    )
                )

            logger.info(f"ExcelLoader loaded {filename} ({len(pages)} worksheets)")

        except Exception as e:
            logger.error(f"Error loading Excel file {filename}: {e}", exc_info=True)
            pages = [LoadedPage(page_number=1, text="", metadata={"error": str(e)})]

        return LoadedDocument(
            filename=filename,
            extension=".xlsx",
            total_pages=len(pages),
            pages=pages,
            document_metadata=doc_metadata,
        )

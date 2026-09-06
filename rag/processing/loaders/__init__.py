"""
Loaders package for file format extraction.
"""

from rag.processing.loaders.pdf_loader import PDFLoader, BaseLoader
from rag.processing.loaders.docx_loader import DocxLoader
from rag.processing.loaders.excel_loader import ExcelLoader

__all__ = ["BaseLoader", "PDFLoader", "DocxLoader", "ExcelLoader"]

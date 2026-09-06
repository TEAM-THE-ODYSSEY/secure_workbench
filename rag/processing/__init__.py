"""
Processing package for document loading, OCR, text cleaning, structural analysis, and parsing.
"""

from rag.processing.loaders.pdf_loader import PDFLoader
from rag.processing.loaders.docx_loader import DocxLoader
from rag.processing.loaders.excel_loader import ExcelLoader
from rag.processing.loaders.pymupdf_loader import PyMuPDFLoader
from rag.processing.loaders.csv_loader import CSVLoader
from rag.processing.parser import DocumentParser, ParsedDocument, ParsedContentElement
from rag.processing.ocr import OCRProcessor, get_ocr_processor, PaddleOCRProcessor, BaseOCRProcessor
from rag.processing.cleaner import TextCleaner
from rag.processing.structure import StructureExtractor, StructuredDocumentBlock

__all__ = [
    "PDFLoader",
    "DocxLoader",
    "ExcelLoader",
    "PyMuPDFLoader",
    "CSVLoader",
    "DocumentParser",
    "ParsedDocument",
    "ParsedContentElement",
    "OCRProcessor",
    "get_ocr_processor",
    "PaddleOCRProcessor",
    "BaseOCRProcessor",
    "TextCleaner",
    "StructureExtractor",
    "StructuredDocumentBlock",
]

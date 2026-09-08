"""
PPTX document loader using python-pptx for structured text and slide extraction.
"""

import io
import logging
from typing import Any, Dict, List
from pydantic import BaseModel, Field

from rag.processing.loaders.pdf_loader import BaseLoader, LoadedDocument, LoadedPage

logger = logging.getLogger(__name__)


class PPTXLoader(BaseLoader):
    """Loader for PPTX presentations extracting text slide by slide."""

    def load(self, content_bytes: bytes, filename: str) -> LoadedDocument:
        pages: List[LoadedPage] = []
        doc_metadata: Dict[str, Any] = {}

        try:
            import pptx
            stream = io.BytesIO(content_bytes)
            prs = pptx.Presentation(stream)
            total_slides = len(prs.slides)

            for idx, slide in enumerate(prs.slides):
                slide_num = idx + 1
                slide_text_parts = []
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text:
                        slide_text_parts.append(shape.text.strip())

                slide_text = "\n".join(slide_text_parts)
                pages.append(
                    LoadedPage(
                        page_number=slide_num,
                        text=slide_text,
                        metadata={"slide": slide_num, "total_slides": total_slides},
                    )
                )

            logger.info(f"PPTXLoader successfully loaded {filename} ({total_slides} slides)")
        except Exception as e:
            logger.error(f"Error loading PPTX {filename}: {e}", exc_info=True)
            pages = [LoadedPage(page_number=1, text="", metadata={"error": str(e)})]

        return LoadedDocument(
            filename=filename,
            extension=".pptx" if filename.lower().endswith(".pptx") else ".ppt",
            total_pages=len(pages),
            pages=pages,
            document_metadata=doc_metadata,
        )

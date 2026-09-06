"""
Structure extractor for identifying sections, headings, tables, bullet lists, and paragraphs.
"""

from enum import Enum
import logging
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class BlockType(str, Enum):
    TITLE = "TITLE"
    HEADING = "HEADING"
    SUBHEADING = "SUBHEADING"
    PARAGRAPH = "PARAGRAPH"
    LIST_ITEM = "LIST_ITEM"
    TABLE = "TABLE"
    CODE = "CODE"
    UNKNOWN = "UNKNOWN"


class StructuredDocumentBlock(BaseModel):
    """Represents a logical block within a document structure."""
    block_id: str
    block_type: BlockType
    text: str
    level: int = 1  # Heading level or depth
    page_number: int = 1
    section_title: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StructureExtractor:
    """Analyzes raw loaded pages and partitions them into structured content blocks."""

    def __init__(self):
        self._heading_pattern = re.compile(r"^(#+|\d+(\.\d+)*\s+[A-Z]|SECTION\s+\d+|CHAPTER\s+\d+|SOP-\d+)", re.IGNORECASE)
        self._list_pattern = re.compile(r"^\s*([•\-\*]|\d+[\.\)])\s+")
        self._table_pattern = re.compile(r"^\s*\|.*\|\s*$")

    def extract_structure(self, pages_data: List[Dict[str, Any]]) -> List[StructuredDocumentBlock]:
        """Extract structured blocks from pages array."""
        blocks: List[StructuredDocumentBlock] = []
        current_section = "General"
        block_counter = 0

        for page in pages_data:
            page_num = page.get("page_number", 1)
            raw_text = page.get("text", "")
            lines = raw_text.split("\n")

            in_table = False
            table_lines: List[str] = []

            for line in lines:
                stripped = line.strip()
                if not stripped:
                    if in_table and table_lines:
                        block_counter += 1
                        blocks.append(
                            StructuredDocumentBlock(
                                block_id=f"block_{block_counter}",
                                block_type=BlockType.TABLE,
                                text="\n".join(table_lines),
                                level=1,
                                page_number=page_num,
                                section_title=current_section,
                            )
                        )
                        table_lines = []
                        in_table = False
                    continue

                # Table line check
                if self._table_pattern.match(stripped) or stripped.startswith("[Table"):
                    in_table = True
                    table_lines.append(stripped)
                    continue
                elif in_table:
                    # Table ended
                    block_counter += 1
                    blocks.append(
                        StructuredDocumentBlock(
                            block_id=f"block_{block_counter}",
                            block_type=BlockType.TABLE,
                            text="\n".join(table_lines),
                            level=1,
                            page_number=page_num,
                            section_title=current_section,
                        )
                    )
                    table_lines = []
                    in_table = False

                # Heading check
                if stripped.startswith("###") or stripped.startswith("##") or stripped.startswith("#"):
                    heading_level = stripped.count("#")
                    current_section = stripped.lstrip("#").strip()
                    block_counter += 1
                    blocks.append(
                        StructuredDocumentBlock(
                            block_id=f"block_{block_counter}",
                            block_type=BlockType.HEADING if heading_level <= 2 else BlockType.SUBHEADING,
                            text=current_section,
                            level=heading_level,
                            page_number=page_num,
                            section_title=current_section,
                        )
                    )
                elif self._heading_pattern.match(stripped) and len(stripped) < 100:
                    current_section = stripped
                    block_counter += 1
                    blocks.append(
                        StructuredDocumentBlock(
                            block_id=f"block_{block_counter}",
                            block_type=BlockType.HEADING,
                            text=stripped,
                            level=2,
                            page_number=page_num,
                            section_title=current_section,
                        )
                    )
                elif self._list_pattern.match(stripped):
                    block_counter += 1
                    blocks.append(
                        StructuredDocumentBlock(
                            block_id=f"block_{block_counter}",
                            block_type=BlockType.LIST_ITEM,
                            text=stripped,
                            level=1,
                            page_number=page_num,
                            section_title=current_section,
                        )
                    )
                else:
                    block_counter += 1
                    blocks.append(
                        StructuredDocumentBlock(
                            block_id=f"block_{block_counter}",
                            block_type=BlockType.PARAGRAPH,
                            text=stripped,
                            level=1,
                            page_number=page_num,
                            section_title=current_section,
                        )
                    )

            if in_table and table_lines:
                block_counter += 1
                blocks.append(
                    StructuredDocumentBlock(
                        block_id=f"block_{block_counter}",
                        block_type=BlockType.TABLE,
                        text="\n".join(table_lines),
                        level=1,
                        page_number=page_num,
                        section_title=current_section,
                    )
                )

        return blocks

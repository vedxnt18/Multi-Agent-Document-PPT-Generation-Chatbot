"""
backend/schemas/extraction.py

Normalized document representation. Every extractor (PDF, DOCX, PPTX, image)
produces this same shape, regardless of source format, so downstream phases
(template analysis, RAG chunking, generation) don't need to know or care
which format the content originally came from.

Design notes:
- `blocks` is an ordered list of content units (paragraph, heading, table,
  image, slide_text, etc.) — this preserves document order, which matters
  for structure/style analysis later.
- `source_type` distinguishes real extracted text from OCR output, so
  downstream consumers and the trace system can be honest about provenance
  (per the "no fake extraction" principle).
"""
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class BlockType(str, Enum):
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    IMAGE = "image"
    SLIDE_TITLE = "slide_title"
    SLIDE_BODY = "slide_body"
    SPEAKER_NOTES = "speaker_notes"


class SourceType(str, Enum):
    NATIVE_TEXT = "native_text"     # extracted directly from the file (selectable text)
    OCR = "ocr"                      # extracted via OCR (image or scanned page)


class ContentBlock(BaseModel):
    block_type: BlockType
    text: str = ""
    level: Optional[int] = None          # heading level, or slide index for slide blocks
    page_number: Optional[int] = None    # for PDFs
    slide_number: Optional[int] = None   # for PPTX
    source_type: SourceType = SourceType.NATIVE_TEXT
    confidence: Optional[float] = None   # OCR confidence, 0-1, if applicable
    bbox: Optional[list[float]] = None   # [x0, y0, x1, y1] bounding box, if available
    metadata: dict[str, Any] = Field(default_factory=dict)  # extra type-specific info (e.g. table rows, font)


class ExtractionResult(BaseModel):
    file_id: str
    original_filename: str
    file_extension: str
    document_type: str                   # "pdf" | "docx" | "pptx" | "image"
    page_or_slide_count: int = 0
    blocks: list[ContentBlock] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)  # e.g. "page 3 required OCR", "OCR unavailable"
    used_ocr: bool = False

    def full_text(self) -> str:
        """Concatenate all block text in order — convenience for RAG chunking later."""
        return "\n".join(b.text for b in self.blocks if b.text)

"""
backend/schemas/template_spec.py

Structured template representations produced by the Document Analysis Agent
and PPT Analysis Agent. These are the contract consumed by the generation
agents in later phases — generation reads these specs to decide fonts,
colors, heading structure, slide layout patterns, etc.

Everything here is derived from real extracted data (python-docx/python-pptx
inspection). Tone/style classification (a judgment call, not a measurable
fact) is the one field that comes from an LLM call — clearly separated so
it's never confused with structural facts.
"""
from typing import Optional
from pydantic import BaseModel, Field


# --------------------------------------------------------------------------
# DOCX / document template spec
# --------------------------------------------------------------------------

class HeadingInfo(BaseModel):
    level: int
    text: str
    font_name: Optional[str] = None
    font_size_pt: Optional[float] = None


class FontUsage(BaseModel):
    font_name: str
    count: int  # how many blocks use this font — helps identify the "primary" font


class TableStyleInfo(BaseModel):
    table_index: int
    row_count: int
    col_count: int


class DocumentStyleSpec(BaseModel):
    file_id: str
    document_type: str = "unspecified"        # e.g. "proposal", "report" — LLM-classified
    tone: str = "unspecified"                  # e.g. "professional", "casual" — LLM-classified
    heading_hierarchy: list[HeadingInfo] = Field(default_factory=list)
    fonts_used: list[FontUsage] = Field(default_factory=list)
    primary_font: Optional[str] = None
    body_paragraph_count: int = 0
    tables: list[TableStyleInfo] = Field(default_factory=list)
    section_titles: list[str] = Field(default_factory=list)   # top-level heading texts, in order
    has_title: bool = False
    warnings: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------
# PPTX template spec
# --------------------------------------------------------------------------

class SlidePatternInfo(BaseModel):
    slide_number: int
    has_title: bool
    body_block_count: int
    has_table: bool
    has_image: bool


class PPTStyleSpec(BaseModel):
    file_id: str
    slide_count: int = 0
    slide_width_in: Optional[float] = None
    slide_height_in: Optional[float] = None
    fonts_used: list[FontUsage] = Field(default_factory=list)
    primary_font: Optional[str] = None
    avg_body_blocks_per_slide: float = 0.0
    content_density: str = "unspecified"        # "light" | "moderate" | "dense" — heuristic, not LLM
    visual_style: str = "unspecified"            # LLM-classified, e.g. "minimal corporate"
    slide_patterns: list[SlidePatternInfo] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

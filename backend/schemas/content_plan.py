"""
backend/schemas/content_plan.py

Structured content representation that generation agents consume. This is
the "intermediate representation" mentioned in the assignment's doc<->ppt
conversion section — both the Document Generation Agent and PPT Generation
Agent read from this same shape, so converting one format to the other is
a transformation of this structure rather than raw text copying.

A GeneratedSection maps naturally to:
    - a DOCX heading + paragraphs (+ optional table)
    - a PPTX slide (title + bullet points), when density requires splitting
      a section into multiple slides, the generator does that split — the
      content plan itself stays one section = one logical unit of content.
"""
from typing import Optional
from pydantic import BaseModel, Field


class GeneratedTable(BaseModel):
    headers: list[str]
    rows: list[list[str]]


class GeneratedSection(BaseModel):
    heading: str
    level: int = 1                                  # 1 = top-level section, 2 = subsection
    paragraphs: list[str] = Field(default_factory=list)
    bullet_points: list[str] = Field(default_factory=list)
    table: Optional[GeneratedTable] = None
    citation_ids: list[str] = Field(default_factory=list)   # citations backing this section's claims


class ContentPlan(BaseModel):
    title: str
    subtitle: Optional[str] = None
    sections: list[GeneratedSection] = Field(default_factory=list)
    document_type: str = "report"
    tone: str = "professional"

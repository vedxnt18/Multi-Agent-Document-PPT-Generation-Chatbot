"""
backend/schemas/research.py
"""
from typing import Optional
from pydantic import BaseModel, Field


class ResearchSource(BaseModel):
    citation_id: str
    title: str
    url: str
    publisher: Optional[str] = None
    published_date: Optional[str] = None
    retrieved_at: str
    summary: str
    is_mock: bool = False


class ResearchResponse(BaseModel):
    query: str
    provider: str
    is_mock: bool
    sources: list[ResearchSource] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

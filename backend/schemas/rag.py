"""
backend/schemas/rag.py
"""
from typing import Optional
from pydantic import BaseModel, Field


class ChunkMetadata(BaseModel):
    document_id: str
    filename: str
    chunk_id: str
    chunk_index: int
    page: Optional[int] = None
    section: Optional[str] = None
    upload_time: str
    source_type: str = "enterprise_document"


class RAGIngestResponse(BaseModel):
    document_id: str
    filename: str
    chunk_count: int
    vector_store: str
    warnings: list[str] = Field(default_factory=list)


class RetrievedChunk(BaseModel):
    citation_id: str
    text: str
    score: float
    document_id: str
    filename: str
    chunk_index: int
    page: Optional[int] = None


class RAGQueryResponse(BaseModel):
    query: str
    retrieved_chunks: list[RetrievedChunk] = Field(default_factory=list)
    vector_store: str
    warnings: list[str] = Field(default_factory=list)

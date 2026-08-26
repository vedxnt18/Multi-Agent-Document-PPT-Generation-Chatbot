"""
backend/agents/rag_agent.py

Enterprise RAG Agent. Implements the pipeline:
    Extraction -> Cleaning -> Chunking -> Metadata -> Embeddings ->
    Vector DB -> Similarity Search -> Retrieved Context

Ingestion: takes an ExtractionResult (from Phase 2), chunks its full text,
embeds each chunk, and upserts into the configured vector store with rich
metadata (document_id, filename, chunk_id, chunk_index, upload_time).

Retrieval: embeds a query, searches the vector store, and registers each
retrieved chunk in the citation registry so results are traceable back to
source documents (RAG-001, RAG-002, ...).
"""
import logging
import re
import uuid
from datetime import datetime, timezone

from backend.schemas.extraction import ExtractionResult
from backend.schemas.rag import RAGIngestResponse, RAGQueryResponse, RetrievedChunk
from backend.services.embedding_service import get_embedding_service
from backend.services.vector_store import get_vector_store, VectorRecord, VectorStoreError
from backend.services.citation_service import citation_registry

logger = logging.getLogger(__name__)

CHUNK_SIZE_CHARS = 800
CHUNK_OVERLAP_CHARS = 150


def clean_text(text: str) -> str:
    """Basic cleaning: collapse whitespace, strip control characters."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE_CHARS, overlap: int = CHUNK_OVERLAP_CHARS) -> list[str]:
    """
    Simple sliding-window chunker on cleaned text. Splits on paragraph
    boundaries where possible to avoid cutting mid-sentence too often.
    """
    text = clean_text(text)
    if len(text) <= chunk_size:
        return [text] if text else []

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        # try to break at the last paragraph/sentence boundary before `end`
        if end < len(text):
            boundary = text.rfind("\n\n", start, end)
            if boundary == -1:
                boundary = text.rfind(". ", start, end)
            if boundary != -1 and boundary > start + chunk_size // 2:
                end = boundary + 1
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def ingest_document(extraction: ExtractionResult, document_id: str | None = None) -> RAGIngestResponse:
    document_id = document_id or extraction.file_id
    warnings: list[str] = []

    full_text = extraction.full_text()
    if not full_text.strip():
        warnings.append("No extractable text found; nothing was indexed.")
        return RAGIngestResponse(
            document_id=document_id,
            filename=extraction.original_filename,
            chunk_count=0,
            vector_store="none",
            warnings=warnings,
        )

    chunks = chunk_text(full_text)
    if not chunks:
        warnings.append("Text was present but produced no chunks after cleaning.")
        return RAGIngestResponse(
            document_id=document_id,
            filename=extraction.original_filename,
            chunk_count=0,
            vector_store="none",
            warnings=warnings,
        )

    embedder = get_embedding_service()
    vectors = embedder.embed_texts(chunks)

    store = get_vector_store()
    upload_time = datetime.now(timezone.utc).isoformat()

    records = []
    for idx, (chunk, vector) in enumerate(zip(chunks, vectors)):
        chunk_id = f"{document_id}_chunk{idx}"
        records.append(
            VectorRecord(
                id=chunk_id,
                vector=vector,
                text=chunk,
                metadata={
                    "document_id": document_id,
                    "filename": extraction.original_filename,
                    "chunk_id": chunk_id,
                    "chunk_index": idx,
                    "upload_time": upload_time,
                    "source_type": "enterprise_document",
                },
            )
        )

    try:
        store.upsert(records)
    except VectorStoreError as e:
        warnings.append(f"Vector store upsert failed: {e}")
        return RAGIngestResponse(
            document_id=document_id,
            filename=extraction.original_filename,
            chunk_count=0,
            vector_store=store.name,
            warnings=warnings,
        )

    return RAGIngestResponse(
        document_id=document_id,
        filename=extraction.original_filename,
        chunk_count=len(records),
        vector_store=store.name,
        warnings=warnings,
    )


def query_knowledge_base(query: str, top_k: int = 5) -> RAGQueryResponse:
    warnings: list[str] = []
    embedder = get_embedding_service()
    store = get_vector_store()

    try:
        query_vector = embedder.embed_query(query)
        matches = store.query(query_vector, top_k=top_k)
    except VectorStoreError as e:
        warnings.append(f"Vector store query failed: {e}")
        return RAGQueryResponse(query=query, retrieved_chunks=[], vector_store=store.name, warnings=warnings)

    retrieved = []
    for match in matches:
        citation_id = citation_registry.register(
            source_type="RAG",
            title=match.metadata.get("filename", "unknown document"),
            detail=f"chunk {match.metadata.get('chunk_index')} (score {match.score:.3f})",
            metadata=match.metadata,
        )
        retrieved.append(
            RetrievedChunk(
                citation_id=citation_id,
                text=match.text,
                score=match.score,
                document_id=match.metadata.get("document_id", "unknown"),
                filename=match.metadata.get("filename", "unknown"),
                chunk_index=match.metadata.get("chunk_index", -1),
                page=match.metadata.get("page"),
            )
        )

    if not retrieved:
        warnings.append("No relevant chunks found in the knowledge base for this query.")

    return RAGQueryResponse(query=query, retrieved_chunks=retrieved, vector_store=store.name, warnings=warnings)

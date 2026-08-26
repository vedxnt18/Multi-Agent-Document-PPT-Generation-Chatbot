"""
tests/test_rag.py

Phase 5 tests. Uses FAISSStore (local, no network) by default since no
Pinecone key is configured in this test environment.

Embedding generation normally uses fastembed, which downloads a model from
Hugging Face on first use. That's undesirable to depend on on in automated
tests regardless of environment (external network call, ~130MB download,
flaky in CI) so these tests monkeypatch EmbeddingService.embed_texts with a
deterministic bag-of-words hashing embedder that produces the same 384-dim
shape and preserves enough semantic signal (shared words -> higher cosine
similarity) for retrieval-ranking assertions to be meaningful.

The REAL fastembed model is exercised separately — see README "Testing
Phase 5" for a one-off live download/embedding check on your machine.
"""
import hashlib
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.config import settings
from backend.agents.rag_agent import chunk_text, clean_text, ingest_document, query_knowledge_base
from backend.services.extraction_service import extract_file
from backend.services.vector_store import get_vector_store, reset_vector_store_cache, FAISSStore
from backend.services.embedding_service import get_embedding_service, EmbeddingService, EMBEDDING_DIM
from backend.services.citation_service import citation_registry

client = TestClient(app)
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _fake_embed_texts(self, texts):
    """Deterministic bag-of-words hashing embedder — no network/model needed."""
    vectors = []
    for text in texts:
        vec = np.zeros(EMBEDDING_DIM, dtype=np.float32)
        for word in text.lower().split():
            idx = int(hashlib.md5(word.encode()).hexdigest(), 16) % EMBEDDING_DIM
            vec[idx] += 1.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        vectors.append(vec.tolist())
    return vectors


@pytest.fixture(autouse=True)
def _fake_embeddings(monkeypatch):
    monkeypatch.setattr(EmbeddingService, "embed_texts", _fake_embed_texts)
    yield


@pytest.fixture(autouse=True)
def _clean_vector_store():
    """Each test gets a fresh FAISS index so tests don't interfere with each other."""
    reset_vector_store_cache()
    faiss_dir = settings.resolve_path(settings.knowledge_base_dir) / "faiss_index"
    if faiss_dir.exists():
        shutil.rmtree(faiss_dir)
    citation_registry.reset()
    yield
    reset_vector_store_cache()


def test_clean_text_collapses_whitespace():
    dirty = "Hello   world\n\n\n\nSecond paragraph"
    cleaned = clean_text(dirty)
    assert "   " not in cleaned
    assert "\n\n\n" not in cleaned


def test_chunk_text_short_text_single_chunk():
    chunks = chunk_text("Short text.")
    assert len(chunks) == 1
    assert chunks[0] == "Short text."


def test_chunk_text_long_text_multiple_chunks():
    long_text = "This is a sentence. " * 200  # ~4000 chars
    chunks = chunk_text(long_text, chunk_size=800, overlap=150)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c) <= 900  # allow small overshoot from boundary search


def test_embedding_service_produces_correct_dimension():
    embedder = get_embedding_service()
    vectors = embedder.embed_texts(["hello world", "another sentence"])
    assert len(vectors) == 2
    assert len(vectors[0]) == embedder.dimension
    assert len(vectors[1]) == embedder.dimension


def test_faiss_store_upsert_and_query():
    from backend.services.vector_store import VectorRecord

    store = FAISSStore(dimension=384, persist_dir=settings.resolve_path(settings.knowledge_base_dir) / "faiss_index_test")
    embedder = get_embedding_service()
    texts = ["The cat sat on the mat.", "Quarterly revenue grew by 12%.", "Dogs are loyal animals."]
    vectors = embedder.embed_texts(texts)
    records = [
        VectorRecord(id=f"rec{i}", vector=v, text=t, metadata={"document_id": "doc1", "chunk_index": i})
        for i, (t, v) in enumerate(zip(texts, vectors))
    ]
    store.upsert(records)

    query_vec = embedder.embed_query("How much did revenue increase?")
    results = store.query(query_vec, top_k=2)
    assert len(results) == 2
    # The revenue sentence should be the most relevant match
    assert "revenue" in results[0].text.lower()

    shutil.rmtree(settings.resolve_path(settings.knowledge_base_dir) / "faiss_index_test")


def test_ingest_document_and_query_end_to_end():
    extraction = extract_file(str(FIXTURES / "sample.docx"), "test-rag-doc", "sample.docx")
    ingest_result = ingest_document(extraction)

    assert ingest_result.chunk_count > 0
    assert ingest_result.vector_store == "faiss"

    query_result = query_knowledge_base("What does the proposal say about market overview?", top_k=3)
    assert len(query_result.retrieved_chunks) > 0
    assert query_result.retrieved_chunks[0].citation_id.startswith("RAG-")

    # citation registry should have the source registered
    source = citation_registry.get(query_result.retrieved_chunks[0].citation_id)
    assert source is not None
    assert source.source_type == "RAG"


def test_query_empty_knowledge_base_returns_warning():
    result = query_knowledge_base("anything")
    assert len(result.retrieved_chunks) == 0
    assert any("No relevant chunks" in w for w in result.warnings)


def test_rag_index_and_query_api():
    with open(FIXTURES / "sample.docx", "rb") as f:
        upload_resp = client.post(
            "/upload",
            files={"file": ("sample.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
    file_id = upload_resp.json()["file"]["file_id"]

    index_resp = client.post(f"/rag/index/{file_id}")
    assert index_resp.status_code == 200
    assert index_resp.json()["chunk_count"] > 0

    query_resp = client.post("/rag/query", json={"query": "market overview", "top_k": 3})
    assert query_resp.status_code == 200
    body = query_resp.json()
    assert len(body["retrieved_chunks"]) > 0

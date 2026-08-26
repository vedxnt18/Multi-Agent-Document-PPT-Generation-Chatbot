"""
tests/test_supervisor.py

Phase 7 tests. LLM_PROVIDER=mock and WEB_SEARCH_PROVIDER=mock in this test
environment, so plan creation uses the heuristic fallback path. This is
intentional and tested explicitly, since it's the path that runs whenever
a live LLM isn't configured/available — the orchestration pipeline must
work end-to-end either way.
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.config import settings
from backend.agents.supervisor import create_plan, orchestrate, _heuristic_plan
from backend.services.vector_store import reset_vector_store_cache
from backend.services.embedding_service import EmbeddingService
from backend.services.citation_service import citation_registry
import hashlib
import numpy as np
from backend.services.embedding_service import EMBEDDING_DIM

client = TestClient(app)
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _fake_embed_texts(self, texts):
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
def _setup(monkeypatch):
    monkeypatch.setattr(EmbeddingService, "embed_texts", _fake_embed_texts)
    reset_vector_store_cache()
    faiss_dir = settings.resolve_path(settings.knowledge_base_dir) / "faiss_index"
    if faiss_dir.exists():
        shutil.rmtree(faiss_dir)
    citation_registry.reset()
    yield
    reset_vector_store_cache()


def test_heuristic_plan_detects_research_and_docx_intent():
    files = [{"file_id": "a", "filename": "proposal.docx", "extension": ".docx"}]
    plan = _heuristic_plan("Research the latest AI trends and create a proposal document", files)
    assert plan.needs_web_research is True
    assert plan.needs_document_analysis is True
    assert plan.generate_docx is True


def test_heuristic_plan_detects_slide_count():
    plan = _heuristic_plan("Create a 12-slide presentation on market trends", [])
    assert plan.slide_count == 12
    assert plan.generate_pptx is True


def test_create_plan_uses_heuristic_when_mock_provider():
    plan = create_plan("Research AI trends", [])
    assert "Heuristic plan" in plan.reasoning


def test_orchestrate_full_demo_scenario():
    """
    Mirrors the assignment's demo scenario: upload a DOCX + PPTX template,
    ask for research + a proposal + a 12-slide presentation.
    """
    with open(FIXTURES / "sample.docx", "rb") as f:
        up1 = client.post(
            "/upload",
            files={"file": ("Company_Proposal.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
    with open(FIXTURES / "sample.pptx", "rb") as f:
        up2 = client.post(
            "/upload",
            files={"file": ("Company_Template.pptx", f, "application/vnd.openxmlformats-officedocument.presentationml.presentation")},
        )
    file_id_docx = up1.json()["file"]["file_id"]
    file_id_pptx = up2.json()["file"]["file_id"]

    resp = client.post(
        "/chat",
        json={
            "message": "Research the latest Generative AI trends and create a proposal and 12-slide presentation using the same tone and style as the uploaded files.",
            "file_ids": [file_id_docx, file_id_pptx],
        },
    )
    assert resp.status_code == 200
    body = resp.json()

    # Plan should have correctly identified all needed agents
    assert body["plan"]["needs_document_analysis"] is True
    assert body["plan"]["needs_ppt_analysis"] is True
    assert body["plan"]["needs_web_research"] is True
    assert body["plan"]["slide_count"] == 12
    assert body["plan"]["generate_docx"] is True
    assert body["plan"]["generate_pptx"] is True

    # All agents should have actually run
    agent_names = {c["agent"] for c in body["agent_calls"]}
    assert "document_analyzer" in agent_names
    assert "ppt_analyzer" in agent_names
    assert "web_research" in agent_names
    assert "rag_agent" in agent_names

    assert body["document_analysis"] is not None
    assert body["ppt_analysis"] is not None
    assert body["research"] is not None
    assert body["rag_results"] is not None

    # citation registry should have entries from both web and rag
    citation_types = {cid.split("-")[0] for cid in body["citation_summary"].keys()}
    assert "WEB" in citation_types
    assert "RAG" in citation_types

    # generation should have run and produced real artifacts (Phase 8/9 now wired in)
    assert body["generated_docx_artifact_id"] is not None
    assert body["generated_pptx_artifact_id"] is not None
    assert "Generation complete" in body["next_step_note"]


def test_orchestrate_handles_no_files_gracefully():
    result = orchestrate("What's the weather like?", file_ids=[])
    assert result.plan is not None
    assert isinstance(result.agent_calls, list)


def test_orchestrate_handles_nonexistent_file_id_gracefully():
    result = orchestrate("Analyze my document", file_ids=["does-not-exist"])
    # Should not crash; file just won't appear in available_files
    assert result.plan is not None

"""
tests/test_web_research.py

Phase 6 tests. No TAVILY_API_KEY is configured in this test environment,
so these exercise the MockSearchProvider path end-to-end, verifying:
  - mock results are honestly labeled (is_mock=True) at every layer
  - deduplication logic works against synthetic duplicate results
  - citation registration happens correctly
  - a failed/unavailable search never crashes the pipeline

Live Tavily behavior is documented separately for testing with a real key.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.agents.web_research import research, _deduplicate, _titles_similar
from backend.services.web_search import (
    SearchResult,
    WebSearchProvider,
    WebSearchError,
    get_web_search_provider,
    reset_web_search_provider_cache,
)
from backend.services.citation_service import citation_registry

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_state():
    reset_web_search_provider_cache()
    citation_registry.reset()
    yield
    reset_web_search_provider_cache()


def test_mock_provider_returns_labeled_mock_results():
    provider = get_web_search_provider()
    assert provider.name == "mock"
    results = provider.search("generative AI trends", max_results=3)
    assert len(results) == 3
    assert all(r.is_mock for r in results)


def test_titles_similar():
    assert _titles_similar("Latest AI Trends 2026", "Latest AI Trends 2026 ")
    assert not _titles_similar("Latest AI Trends", "Quarterly Revenue Report")


def test_deduplicate_removes_exact_url_duplicates():
    results = [
        SearchResult(title="A", url="https://x.com/a", snippet="s1"),
        SearchResult(title="A duplicate", url="https://x.com/a", snippet="s2"),
        SearchResult(title="B", url="https://x.com/b", snippet="s3"),
    ]
    deduped = _deduplicate(results)
    assert len(deduped) == 2


def test_deduplicate_removes_near_duplicate_titles():
    results = [
        SearchResult(title="Generative AI Trends in 2026", url="https://a.com", snippet="s1"),
        SearchResult(title="Generative AI Trends in 2026 ", url="https://b.com", snippet="s2"),
    ]
    deduped = _deduplicate(results)
    assert len(deduped) == 1


def test_research_end_to_end_mock_provider():
    response = research("What are the latest generative AI trends?", max_results=3)

    assert response.provider == "mock"
    assert response.is_mock is True
    assert len(response.sources) > 0
    assert all(s.is_mock for s in response.sources)
    assert all(s.citation_id.startswith("WEB-") for s in response.sources)
    assert len(response.findings) > 0
    assert any("configured" in w.lower() for w in response.warnings)

    # sources should be registered in the citation registry
    first_citation = response.sources[0].citation_id
    registered = citation_registry.get(first_citation)
    assert registered is not None
    assert registered.source_type == "WEB"


class _FailingProvider(WebSearchProvider):
    name = "failing"

    def search(self, query, max_results=5):
        raise WebSearchError("simulated network failure")


def test_research_handles_search_failure_gracefully(monkeypatch):
    import backend.agents.web_research as web_research_module

    monkeypatch.setattr(web_research_module, "get_web_search_provider", lambda: _FailingProvider())
    response = research("anything")
    assert response.sources == []
    assert any("unavailable" in w.lower() for w in response.warnings)


def test_research_api_endpoint():
    resp = client.post("/research", json={"query": "AI trends", "max_results": 3})
    assert resp.status_code == 200
    body = resp.json()
    assert body["provider"] == "mock"
    assert len(body["sources"]) > 0

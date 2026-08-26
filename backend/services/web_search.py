"""
backend/services/web_search.py

Web search provider abstraction. Mirrors the LLMProvider/VectorStore
pattern: `get_web_search_provider()` returns TavilySearchProvider if
TAVILY_API_KEY is set, otherwise MockSearchProvider.

CRITICAL: MockSearchProvider results are never presented as real web
research. Every SearchResult carries `is_mock: bool` so callers (the
WebResearchAgent, the trace system, the chat UI) can and must label mock
results honestly rather than pretending a real search happened.
"""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from backend.config import settings

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    published_date: Optional[str] = None
    retrieved_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    is_mock: bool = False


class WebSearchError(Exception):
    pass


class WebSearchProvider(ABC):
    name: str = "base"

    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        ...


class TavilySearchProvider(WebSearchProvider):
    name = "tavily"

    def __init__(self, api_key: str):
        if not api_key:
            raise WebSearchError("TAVILY_API_KEY is not set but WEB_SEARCH_PROVIDER=tavily")
        from tavily import TavilyClient
        self._client = TavilyClient(api_key=api_key)

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        try:
            response = self._client.search(query=query, max_results=max_results)
        except Exception as e:
            raise WebSearchError(f"Tavily search failed: {e}") from e

        results = []
        for item in response.get("results", []):
            results.append(
                SearchResult(
                    title=item.get("title", "Untitled"),
                    url=item.get("url", ""),
                    snippet=item.get("content", ""),
                    published_date=item.get("published_date"),
                    is_mock=False,
                )
            )
        return results


class MockSearchProvider(WebSearchProvider):
    """
    Deterministic offline provider. Returns clearly-labeled placeholder
    results so the agent pipeline is fully testable/wireable without a
    Tavily key, and so the system never silently pretends to have searched
    the web when it hasn't.
    """
    name = "mock"

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        return [
            SearchResult(
                title=f"[MOCK] Placeholder result {i + 1} for '{query}'",
                url=f"https://example.invalid/mock-result-{i + 1}",
                snippet=(
                    "This is a MOCK search result generated because no real web search "
                    "provider (e.g. Tavily) is configured. It does not represent real web content."
                ),
                published_date=None,
                is_mock=True,
            )
            for i in range(min(max_results, 3))
        ]


_provider_instance: Optional[WebSearchProvider] = None


def get_web_search_provider() -> WebSearchProvider:
    global _provider_instance
    if _provider_instance is not None:
        return _provider_instance

    provider_name = settings.web_search_provider.lower()

    if provider_name == "tavily":
        try:
            _provider_instance = TavilySearchProvider(api_key=settings.tavily_api_key)
            return _provider_instance
        except WebSearchError as e:
            logger.warning(f"Tavily unavailable ({e}); falling back to mock search provider.")

    _provider_instance = MockSearchProvider()
    return _provider_instance


def reset_web_search_provider_cache() -> None:
    global _provider_instance
    _provider_instance = None

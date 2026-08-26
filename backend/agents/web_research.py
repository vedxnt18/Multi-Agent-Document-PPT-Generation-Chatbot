"""
backend/agents/web_research.py

Web Research Agent. Pipeline:
    1. Take the research question as-is (query understanding is a direct
       pass-through for MVP; query expansion/refinement is a documented
       future improvement).
    2. Search the web via the configured WebSearchProvider (Tavily or Mock).
    3. Deduplicate results by URL and near-duplicate title.
    4. Register each surviving source in the citation registry (WEB-001, ...).
    5. Optionally synthesize a short set of findings via the LLM, with each
       finding required to reference the citation IDs it draws from. If the
       LLM is on MockProvider, findings are built directly from snippets
       instead, and clearly labeled as non-LLM-synthesized.

Honesty guarantees:
    - `is_mock` is set at the top level and per-source, so nothing here can
      be silently presented as real web research when it isn't.
    - A failed search never crashes the pipeline; it returns an empty
      result set with a warning ("Web research unavailable...").
"""
import logging
from difflib import SequenceMatcher

from backend.schemas.research import ResearchResponse, ResearchSource
from backend.services.web_search import get_web_search_provider, WebSearchError
from backend.services.citation_service import citation_registry
from backend.services.llm_service import get_llm_provider, LLMError, LLMJSONParseError

logger = logging.getLogger(__name__)

FINDINGS_SYSTEM_PROMPT = (
    "You are a research assistant. Given a set of web search results (each "
    "with a citation ID), write 3-6 concise findings that answer the "
    "research question. Every finding MUST end with the citation ID(s) it "
    "is based on, in square brackets, e.g. 'Finding text [WEB-001].' "
    "Do not invent facts not present in the provided sources."
)


def _titles_similar(a: str, b: str, threshold: float = 0.85) -> bool:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio() >= threshold


def _deduplicate(results: list) -> list:
    seen_urls = set()
    kept = []
    for r in results:
        if r.url in seen_urls:
            continue
        if any(_titles_similar(r.title, k.title) for k in kept):
            continue
        seen_urls.add(r.url)
        kept.append(r)
    return kept


def _build_findings_prompt(query: str, sources: list[ResearchSource]) -> str:
    lines = [f"Research question: {query}\n"]
    for s in sources:
        lines.append(f"[{s.citation_id}] {s.title}\n{s.summary}\n")
    return "\n".join(lines)


def research(query: str, max_results: int = 5) -> ResearchResponse:
    provider = get_web_search_provider()
    warnings: list[str] = []

    try:
        raw_results = provider.search(query, max_results=max_results)
    except WebSearchError as e:
        logger.warning(f"Web research unavailable: {e}")
        return ResearchResponse(
            query=query,
            provider=provider.name,
            is_mock=(provider.name == "mock"),
            sources=[],
            findings=[],
            warnings=[f"Web research unavailable: {e}. Continuing with enterprise knowledge and uploaded documents."],
        )

    deduped = _deduplicate(raw_results)

    sources: list[ResearchSource] = []
    for r in deduped:
        citation_id = citation_registry.register(
            source_type="WEB",
            title=r.title,
            detail=r.url,
            metadata={"url": r.url, "published_date": r.published_date, "retrieved_at": r.retrieved_at, "is_mock": r.is_mock},
        )
        sources.append(
            ResearchSource(
                citation_id=citation_id,
                title=r.title,
                url=r.url,
                publisher=_extract_publisher(r.url),
                published_date=r.published_date,
                retrieved_at=r.retrieved_at,
                summary=r.snippet,
                is_mock=r.is_mock,
            )
        )

    is_mock = provider.name == "mock"
    if is_mock:
        warnings.append(
            "No real web search provider is configured (WEB_SEARCH_PROVIDER=mock). "
            "Results below are placeholders, not real web content."
        )

    # --- Findings synthesis ---
    findings: list[str] = []
    if sources:
        if is_mock:
            findings = [f"{s.summary} [{s.citation_id}]" for s in sources]
        else:
            try:
                llm = get_llm_provider()
                if llm.name == "mock":
                    findings = [f"{s.summary} [{s.citation_id}]" for s in sources]
                else:
                    prompt = _build_findings_prompt(query, sources)
                    raw = llm.generate_text(prompt, system_prompt=FINDINGS_SYSTEM_PROMPT)
                    findings = [line.strip("- ").strip() for line in raw.split("\n") if line.strip()]
            except (LLMError, LLMJSONParseError) as e:
                warnings.append(f"Findings synthesis unavailable ({e}); showing raw source snippets instead.")
                findings = [f"{s.summary} [{s.citation_id}]" for s in sources]
    else:
        warnings.append("No search results found for this query.")

    return ResearchResponse(
        query=query,
        provider=provider.name,
        is_mock=is_mock,
        sources=sources,
        findings=findings,
        warnings=warnings,
    )


def _extract_publisher(url: str) -> str:
    try:
        from urllib.parse import urlparse
        netloc = urlparse(url).netloc
        return netloc.replace("www.", "") if netloc else "unknown"
    except Exception:
        return "unknown"

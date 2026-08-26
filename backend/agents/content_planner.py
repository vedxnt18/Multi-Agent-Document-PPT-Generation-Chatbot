"""
backend/agents/content_planner.py

Shared content-planning step used by both the Document Generation Agent
and PPT Generation Agent. Takes the user's request plus whatever context is
available (web research findings, RAG chunks, an existing document's style
spec for tone matching) and produces a ContentPlan — the structured
intermediate representation both generators read from.

With a real LLM, this is one generate_json call. With MockProvider, falls
back to directly assembling sections from research findings / RAG chunks
so the generation pipeline is still fully exercisable and testable offline
— clearly not "real" authored content, just structurally valid output.
"""
import logging

from backend.schemas.content_plan import ContentPlan, GeneratedSection
from backend.services.llm_service import get_llm_provider, LLMError, LLMJSONParseError

logger = logging.getLogger(__name__)

CONTENT_PLAN_SYSTEM_PROMPT = (
    "You are a professional business document writer. Given a request, research "
    "findings, and enterprise knowledge context, produce a structured content plan "
    "for a document. Every claim drawn from the provided findings/context must "
    "reference its citation ID in citation_ids for that section. Match the "
    "requested tone. Do not invent facts not present in the provided context."
)


def _build_prompt(
    user_request: str,
    research_findings: list[str],
    rag_chunks: list[dict],
    tone: str,
    document_type: str,
) -> str:
    findings_block = "\n".join(research_findings) or "(no web research findings available)"
    rag_block = "\n".join(f"[{c.get('citation_id')}] {c.get('text', '')[:300]}" for c in rag_chunks) or "(no enterprise knowledge retrieved)"
    return (
        f"Request: {user_request}\n\n"
        f"Target tone: {tone}\nTarget document type: {document_type}\n\n"
        f"Web research findings (each already ends with its citation ID):\n{findings_block}\n\n"
        f"Enterprise knowledge chunks:\n{rag_block}\n\n"
        'Return JSON with exactly this shape: '
        '{"title": "...", "subtitle": "... or null", "sections": ['
        '{"heading": "...", "level": 1, "paragraphs": ["..."], "bullet_points": [], '
        '"table": null, "citation_ids": ["WEB-001"]}'
        "]}"
    )


def _heuristic_plan(
    user_request: str,
    research_findings: list[str],
    rag_chunks: list[dict],
    tone: str,
    document_type: str,
) -> ContentPlan:
    sections = []

    if research_findings:
        sections.append(
            GeneratedSection(
                heading="Research Findings",
                level=1,
                paragraphs=research_findings,
                citation_ids=_extract_citation_ids(research_findings),
            )
        )

    if rag_chunks:
        sections.append(
            GeneratedSection(
                heading="Enterprise Knowledge Context",
                level=1,
                paragraphs=[c.get("text", "") for c in rag_chunks],
                citation_ids=[c.get("citation_id", "") for c in rag_chunks if c.get("citation_id")],
            )
        )

    if not sections:
        sections.append(
            GeneratedSection(
                heading="Overview",
                level=1,
                paragraphs=[
                    "(MockProvider active — no live LLM content generation. "
                    "This is placeholder structural content only.)"
                ],
            )
        )

    return ContentPlan(
        title=user_request[:80] if user_request else "Generated Document",
        subtitle="(mock content — no live LLM)",
        sections=sections,
        document_type=document_type,
        tone=tone,
    )


def _extract_citation_ids(texts: list[str]) -> list[str]:
    import re
    ids = []
    for t in texts:
        ids.extend(re.findall(r"\[(WEB-\d+|RAG-\d+|DOC-\d+)\]", t))
    return ids


def create_content_plan(
    user_request: str,
    research_findings: list[str] | None = None,
    rag_chunks: list[dict] | None = None,
    tone: str = "professional",
    document_type: str = "report",
) -> ContentPlan:
    research_findings = research_findings or []
    rag_chunks = rag_chunks or []

    llm = get_llm_provider()
    if llm.name == "mock":
        return _heuristic_plan(user_request, research_findings, rag_chunks, tone, document_type)

    try:
        prompt = _build_prompt(user_request, research_findings, rag_chunks, tone, document_type)
        result = llm.generate_json(prompt, system_prompt=CONTENT_PLAN_SYSTEM_PROMPT)
        return ContentPlan(**result)
    except (LLMError, LLMJSONParseError, Exception) as e:
        logger.warning(f"LLM content planning failed ({e}); falling back to heuristic plan.")
        plan = _heuristic_plan(user_request, research_findings, rag_chunks, tone, document_type)
        plan.subtitle = f"(LLM content planning failed: {e})"
        return plan

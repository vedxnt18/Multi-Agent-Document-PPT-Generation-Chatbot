"""
backend/agents/document_analyzer.py

Document Analysis Agent. Consumes an ExtractionResult (Phase 2 output) for
a DOCX/PDF and produces a DocumentStyleSpec: structural facts computed
directly from the data (headings, fonts, tables, section order), plus one
LLM call for the two genuinely subjective judgments — document type and
tone — since those aren't things you can measure, only infer.

If the LLM call fails or is running on MockProvider, document_type/tone
fall back to "unspecified" / "unclassified (mock)" rather than fabricating
a confident-sounding label — the analysis is honest about what's a
structural fact vs. an inference.
"""
import logging
from collections import Counter

from backend.schemas.extraction import ExtractionResult, BlockType
from backend.schemas.template_spec import DocumentStyleSpec, HeadingInfo, FontUsage, TableStyleInfo
from backend.services.llm_service import get_llm_provider, LLMError, LLMJSONParseError

logger = logging.getLogger(__name__)

CLASSIFICATION_SYSTEM_PROMPT = (
    "You are a document analysis assistant. Given excerpts from a business "
    "document, classify its type and tone. Be concise and use standard "
    "business-document categories."
)


def _build_classification_prompt(extraction: ExtractionResult) -> str:
    section_titles = [b.text for b in extraction.blocks if b.block_type == BlockType.HEADING][:10]
    sample_text = extraction.full_text()[:1500]
    return (
        f"Section headings found: {section_titles}\n\n"
        f"First ~1500 characters of body text:\n{sample_text}\n\n"
        'Return JSON with exactly these keys: '
        '{"document_type": "<one or two words, e.g. proposal, report, memo, contract>", '
        '"tone": "<one or two words, e.g. professional, casual, technical, persuasive>"}'
    )


def analyze_document(extraction: ExtractionResult, use_llm: bool = True) -> DocumentStyleSpec:
    spec = DocumentStyleSpec(file_id=extraction.file_id)

    if not extraction.blocks:
        spec.warnings.append("No content blocks found in extraction result; analysis is empty.")
        return spec

    # --- Structural facts (no LLM needed) ---
    font_counter: Counter = Counter()
    for block in extraction.blocks:
        if block.block_type == BlockType.HEADING:
            spec.heading_hierarchy.append(
                HeadingInfo(
                    level=block.level if block.level is not None else 1,
                    text=block.text,
                    font_name=block.metadata.get("font_name"),
                    font_size_pt=block.metadata.get("font_size_pt"),
                )
            )
            if block.level == 0:
                spec.has_title = True
            elif block.level == 1:
                spec.section_titles.append(block.text)

        elif block.block_type == BlockType.PARAGRAPH:
            spec.body_paragraph_count += 1

        elif block.block_type == BlockType.TABLE:
            rows = block.metadata.get("rows", [])
            col_count = len(rows[0]) if rows else 0
            spec.tables.append(
                TableStyleInfo(
                    table_index=len(spec.tables),
                    row_count=len(rows),
                    col_count=col_count,
                )
            )

        font_name = block.metadata.get("font_name") if block.metadata else None
        if font_name:
            font_counter[font_name] += 1

    spec.fonts_used = [FontUsage(font_name=name, count=count) for name, count in font_counter.most_common()]
    spec.primary_font = spec.fonts_used[0].font_name if spec.fonts_used else None

    if extraction.warnings:
        spec.warnings.extend(extraction.warnings)

    # --- Subjective classification (LLM) ---
    if use_llm:
        try:
            provider = get_llm_provider()
            if provider.name == "mock":
                spec.document_type = "unspecified (mock provider — no live classification)"
                spec.tone = "unspecified (mock provider — no live classification)"
            else:
                prompt = _build_classification_prompt(extraction)
                result = provider.generate_json(prompt, system_prompt=CLASSIFICATION_SYSTEM_PROMPT)
                spec.document_type = str(result.get("document_type", "unspecified"))
                spec.tone = str(result.get("tone", "unspecified"))
        except (LLMError, LLMJSONParseError) as e:
            logger.warning(f"Document classification failed: {e}")
            spec.warnings.append(f"Tone/type classification unavailable: {e}")

    return spec

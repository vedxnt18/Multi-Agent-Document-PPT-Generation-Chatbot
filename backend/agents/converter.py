"""
backend/agents/converter.py

Document <-> Presentation conversion. Both directions operate on the same
ContentPlan intermediate representation (Phase 8), so this is a structural
transform, not raw text copying:

    DOCX/PDF -> ContentPlan -> transform -> PPTX
    PPTX -> ContentPlan -> transform -> DOCX

docx_to_pptx: paragraph-heavy sections become bullet-point slides (reusing
the same paragraph->bullet extraction as the PPT generator).
pptx_to_docx: bullet-point slides become paragraph-form prose (bullets are
joined into a paragraph rather than left as a bare list, since a Word
document reads as prose, not slide fragments).
"""
import logging

from backend.schemas.content_plan import ContentPlan, GeneratedSection
from backend.schemas.template_spec import DocumentStyleSpec, PPTStyleSpec
from backend.agents.document_generator import generate_docx
from backend.agents.ppt_generator import generate_pptx, _section_to_bullets

logger = logging.getLogger(__name__)


def docx_plan_to_pptx_plan(plan: ContentPlan) -> ContentPlan:
    """Transform a document-oriented ContentPlan into a slide-oriented one."""
    new_sections = []
    for section in plan.sections:
        bullets = _section_to_bullets(section)
        new_sections.append(
            GeneratedSection(
                heading=section.heading,
                level=1,
                bullet_points=bullets,
                table=section.table,
                citation_ids=section.citation_ids,
            )
        )
    return ContentPlan(
        title=plan.title,
        subtitle=plan.subtitle,
        sections=new_sections,
        document_type="presentation",
        tone=plan.tone,
    )


def pptx_plan_to_docx_plan(plan: ContentPlan) -> ContentPlan:
    """Transform a slide-oriented ContentPlan into a document-oriented one."""
    new_sections = []
    for section in plan.sections:
        if section.bullet_points:
            # Join bullets into flowing prose rather than leaving them as a
            # bare list — a Word document reads as prose, not slide fragments.
            paragraph = " ".join(b if b.endswith(('.', '!', '?')) else b + "." for b in section.bullet_points)
            paragraphs = [paragraph]
        else:
            paragraphs = section.paragraphs

        new_sections.append(
            GeneratedSection(
                heading=section.heading,
                level=1,
                paragraphs=paragraphs,
                table=section.table,
                citation_ids=section.citation_ids,
            )
        )
    return ContentPlan(
        title=plan.title,
        subtitle=plan.subtitle,
        sections=new_sections,
        document_type="report",
        tone=plan.tone,
    )


def convert_docx_to_pptx(
    source_plan: ContentPlan,
    output_path: str,
    style_spec: PPTStyleSpec | None = None,
    target_slide_count: int | None = None,
) -> tuple[str, ContentPlan]:
    converted_plan = docx_plan_to_pptx_plan(source_plan)
    generate_pptx(converted_plan, output_path, style_spec=style_spec, target_slide_count=target_slide_count)
    return output_path, converted_plan


def convert_pptx_to_docx(
    source_plan: ContentPlan,
    output_path: str,
    style_spec: DocumentStyleSpec | None = None,
) -> tuple[str, ContentPlan]:
    converted_plan = pptx_plan_to_docx_plan(source_plan)
    generate_docx(converted_plan, output_path, style_spec=style_spec)
    return output_path, converted_plan

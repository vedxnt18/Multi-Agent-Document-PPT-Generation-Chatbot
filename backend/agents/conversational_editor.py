"""
backend/agents/conversational_editor.py

Conversational Editing Agent. Per assignment: after generating a document/
presentation, the user should be able to say "Add an executive summary",
"Make the presentation more concise", "Add competitive analysis", etc.,
and the system modifies the EXISTING artifact rather than regenerating
everything from scratch, preserving what was already there.

Pipeline:
    1. Load the artifact's latest ContentPlan from the artifact store.
    2. Interpret the edit request into a structured EditInstruction
       (LLM-driven with a keyword-heuristic fallback for MockProvider,
       same pattern as the supervisor/content planner).
    3. Apply the instruction as a targeted mutation on the ContentPlan
       (add/remove/modify one section, or condense all sections) —
       everything else in the plan is left untouched.
    4. Regenerate the file from the updated plan (python-docx/pptx has no
       true "patch in place" API for arbitrary edits, so we re-render from
       the updated structured plan — but the plan itself was edited
       surgically, not regenerated from scratch by the LLM).
    5. Save as a new version, validate, and return a change summary.
"""
import logging

from backend.schemas.content_plan import ContentPlan, GeneratedSection
from backend.schemas.editing import EditInstruction, EditResult
from backend.services.llm_service import get_llm_provider, LLMError, LLMJSONParseError
from backend.services import artifact_store
from backend.agents.document_generator import generate_docx, default_output_path
from backend.agents.ppt_generator import generate_pptx, default_pptx_output_path
from backend.agents.validator import validate_docx, validate_pptx
from backend.schemas.template_spec import DocumentStyleSpec, PPTStyleSpec

logger = logging.getLogger(__name__)

EDIT_SYSTEM_PROMPT = (
    "You are an editing assistant for a generated document/presentation. Given "
    "the current section headings and an edit request, decide what structural "
    "change is needed. If adding a section, write real, professional content "
    "for it based on the request and any provided context."
)

# Generic starter content used only when heuristically adding a section with
# MockProvider active (no live LLM to author real content). Clearly a
# placeholder, not presented as authored content.
_MOCK_SECTION_TEMPLATES = {
    "executive summary": [
        "(MockProvider active — no live LLM content generation. "
        "This is placeholder structural content for an executive summary.)"
    ],
    "competitive analysis": [
        "(MockProvider active — no live LLM content generation. "
        "This is placeholder structural content for a competitive analysis.)"
    ],
}


def _build_prompt(user_request: str, current_headings: list[str]) -> str:
    return (
        f"Current document sections (in order): {current_headings}\n\n"
        f"Edit request: {user_request}\n\n"
        'Return JSON with exactly this shape: '
        '{"operation": "add_section | remove_section | modify_section | condense | unsupported", '
        '"target_heading": "<existing heading, for remove/modify, or null>", '
        '"new_heading": "<heading text, for add_section, or null>", '
        '"new_paragraphs": ["..."], "new_bullet_points": ["..."], '
        '"reasoning": "<one sentence>"}'
    )


def _heuristic_instruction(user_request: str, current_headings: list[str]) -> EditInstruction:
    text = user_request.lower()

    if any(kw in text for kw in ["more concise", "shorter", "condense", "trim"]):
        return EditInstruction(operation="condense", reasoning="Heuristic match: conciseness request.")

    if "remove" in text or "delete" in text:
        for heading in current_headings:
            if heading.lower() in text:
                return EditInstruction(operation="remove_section", target_heading=heading, reasoning=f"Heuristic match: remove '{heading}'.")

    if "add" in text or "include" in text:
        import re
        m = re.search(r"add(?:\s+an?)?\s+(.+?)(?:\s+section)?$", text.strip().rstrip("."))
        topic = m.group(1).strip() if m else "New Section"
        topic_title = topic.title()
        template_key = topic.lower()
        paragraphs = _MOCK_SECTION_TEMPLATES.get(
            template_key,
            [f"(MockProvider active — placeholder content for '{topic_title}'.)"],
        )
        return EditInstruction(
            operation="add_section",
            new_heading=topic_title,
            new_paragraphs=paragraphs,
            reasoning=f"Heuristic match: add section '{topic_title}'.",
        )

    return EditInstruction(operation="unsupported", reasoning="Could not match request to a supported edit operation (heuristic mode).")


def interpret_edit_request(user_request: str, current_headings: list[str]) -> EditInstruction:
    llm = get_llm_provider()
    if llm.name == "mock":
        return _heuristic_instruction(user_request, current_headings)

    try:
        prompt = _build_prompt(user_request, current_headings)
        result = llm.generate_json(prompt, system_prompt=EDIT_SYSTEM_PROMPT)
        return EditInstruction(**result)
    except (LLMError, LLMJSONParseError, Exception) as e:
        logger.warning(f"LLM edit interpretation failed ({e}); falling back to heuristic.")
        instr = _heuristic_instruction(user_request, current_headings)
        instr.reasoning += f" (LLM interpretation failed: {e})"
        return instr


def _apply_instruction(plan: ContentPlan, instruction: EditInstruction) -> tuple[ContentPlan, str]:
    if instruction.operation == "add_section":
        new_section = GeneratedSection(
            heading=instruction.new_heading or "New Section",
            paragraphs=instruction.new_paragraphs,
            bullet_points=instruction.new_bullet_points,
        )
        plan.sections.append(new_section)
        summary = f"Added section '{new_section.heading}'."

    elif instruction.operation == "remove_section":
        before = len(plan.sections)
        plan.sections = [s for s in plan.sections if s.heading != instruction.target_heading]
        removed = before - len(plan.sections)
        summary = f"Removed section '{instruction.target_heading}'." if removed else f"No section named '{instruction.target_heading}' found; nothing removed."

    elif instruction.operation == "modify_section":
        found = False
        for s in plan.sections:
            if s.heading == instruction.target_heading:
                if instruction.new_paragraphs:
                    s.paragraphs = instruction.new_paragraphs
                if instruction.new_bullet_points:
                    s.bullet_points = instruction.new_bullet_points
                found = True
                break
        summary = f"Modified section '{instruction.target_heading}'." if found else f"No section named '{instruction.target_heading}' found; nothing modified."

    elif instruction.operation == "condense":
        changed = 0
        for s in plan.sections:
            if len(s.bullet_points) > 3:
                s.bullet_points = s.bullet_points[:3]
                changed += 1
            if s.paragraphs:
                shortened = [p.split(". ")[0].strip() for p in s.paragraphs]
                shortened = [p if p.endswith(".") else p + "." for p in shortened]
                if shortened != s.paragraphs:
                    changed += 1
                s.paragraphs = shortened
        summary = f"Condensed {changed} section(s) to their most essential points."

    else:
        summary = "Edit request was not understood as a supported operation; no changes made."

    return plan, summary


def edit_artifact(artifact_id: str, user_request: str) -> EditResult:
    plan = artifact_store.load_latest_content_plan(artifact_id)
    artifact_type = artifact_store.get_artifact_type(artifact_id)
    style_spec_dict = artifact_store.get_style_spec(artifact_id)

    current_headings = [s.heading for s in plan.sections]
    instruction = interpret_edit_request(user_request, current_headings)

    updated_plan, change_summary = _apply_instruction(plan, instruction)

    new_version = artifact_store.get_latest_version_number(artifact_id) + 1

    if artifact_type == "docx":
        style_spec = DocumentStyleSpec(**style_spec_dict) if style_spec_dict else None
        output_path = default_output_path(artifact_id, version=new_version)
        generate_docx(updated_plan, output_path, style_spec=style_spec)
        validation = validate_docx(output_path)
    elif artifact_type == "pptx":
        style_spec = PPTStyleSpec(**style_spec_dict) if style_spec_dict else None
        output_path = default_pptx_output_path(artifact_id, version=new_version)
        generate_pptx(updated_plan, output_path, style_spec=style_spec)
        validation = validate_pptx(output_path)
    else:
        raise ValueError(f"Unknown artifact_type '{artifact_type}'")

    artifact_store.save_version(
        artifact_id=artifact_id,
        artifact_type=artifact_type,
        version=new_version,
        file_path=output_path,
        content_plan=updated_plan,
        style_spec=style_spec_dict,
        change_request=user_request,
    )

    return EditResult(
        artifact_id=artifact_id,
        new_version=new_version,
        file_path=output_path,
        instruction=instruction,
        change_summary=change_summary,
        validation_status=validation.status,
    )

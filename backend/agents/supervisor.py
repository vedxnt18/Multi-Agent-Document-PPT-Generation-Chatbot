"""
backend/agents/supervisor.py

Supervisor/Orchestrator Agent. Responsibilities (per assignment):
    - Understand user intent
    - Inspect available files
    - Determine which agents are required
    - Create an execution plan
    - Call agents in the correct order
    - Pass structured outputs between agents
    - Handle failures (each agent call is wrapped; a failure in one agent
      does not abort the others)
    - Maintain a per-request trace of what was called and why

Generation/validation/version agents don't exist yet (Phases 8-11), so the
orchestration result stops at "here's what was analyzed/researched/
retrieved, and here's what would be generated next" — `next_step_note`
makes that explicit rather than silently doing nothing.
"""
import logging
from pathlib import Path

from backend.schemas.supervisor import ExecutionPlan, OrchestrationResult, AgentCallRecord
from backend.services.llm_service import get_llm_provider, LLMError, LLMJSONParseError
from backend.services.extraction_service import extract_file
from backend.services.citation_service import citation_registry
from backend.agents.document_analyzer import analyze_document
from backend.agents.ppt_analyzer import analyze_ppt
from backend.agents.web_research import research
from backend.agents.rag_agent import ingest_document, query_knowledge_base
from backend.services import trace_service
from backend.agents.content_planner import create_content_plan
from backend.agents.document_generator import generate_docx, default_output_path
from backend.agents.ppt_generator import generate_pptx, default_pptx_output_path
from backend.agents.validator import validate_docx, validate_pptx
from backend.services import artifact_store
import uuid

logger = logging.getLogger(__name__)

PLAN_SYSTEM_PROMPT = (
    "You are the supervisor agent of a multi-agent document/presentation generation "
    "system. Given a user request and a list of currently available uploaded files "
    "(with their types), decide which downstream agents are needed and produce a "
    "structured execution plan."
)


def _build_plan_prompt(user_request: str, available_files: list[dict]) -> str:
    files_desc = "\n".join(f"- {f['filename']} ({f['extension']})" for f in available_files) or "(none uploaded)"
    return (
        f"User request: {user_request}\n\n"
        f"Available uploaded files:\n{files_desc}\n\n"
        "Return JSON with exactly these keys:\n"
        '{"intent": "generate_artifacts | research_only | analyze_only | edit_artifact | other", '
        '"needs_document_analysis": bool, "needs_ppt_analysis": bool, '
        '"needs_web_research": bool, "needs_rag": bool, '
        '"generate_docx": bool, "generate_pptx": bool, '
        '"slide_count": int or null, "requires_validation": bool, '
        '"research_query": "<string or null - the core question to research, if web research is needed>", '
        '"reasoning": "<one sentence explaining the plan>"}\n\n'
        "Rules: needs_document_analysis should be true only if a DOCX or PDF is uploaded "
        "and its structure/style is relevant to the request. needs_ppt_analysis only if a "
        "PPTX is uploaded and relevant. needs_web_research true if the request asks for "
        "current/latest/research information. needs_rag true if enterprise knowledge "
        "retrieval is relevant (uploaded documents should be searched for supporting content)."
    )


def _heuristic_plan(user_request: str, available_files: list[dict]) -> ExecutionPlan:
    """
    Fallback plan used when running on MockProvider (no live LLM), so the
    orchestration pipeline is still fully exercisable offline/in tests.
    Simple keyword heuristics — clearly a fallback, not a substitute for
    real intent understanding.
    """
    text = user_request.lower()
    has_docx = any(f["extension"] == ".docx" for f in available_files)
    has_pdf = any(f["extension"] == ".pdf" for f in available_files)
    has_pptx = any(f["extension"] == ".pptx" for f in available_files)
    has_image = any(f["extension"] in (".png", ".jpg", ".jpeg")for f in available_files)

    # wants_research = any(kw in text for kw in ["research", "latest", "current", "trends", "recent"])
    # wants_docx_out = any(kw in text for kw in ["proposal", "report", "document", "docx", "doc "])
    # wants_pptx_out = any(kw in text for kw in ["presentation", "slide", "pptx", "ppt "])
    
    wants_research = any(kw in text for kw in ["research", "latest", "current", "trends", "recent"])
    wants_docx_out = any(kw in text for kw in [
        "create a docx",
        "generate a docx",
        "create docx",
        "generate docx",
        "create a report",
        "generate a report",
        "create a proposal",
        "generate a proposal",
        "editable docx",
        ".docx",
        ])

    wants_pptx_out = any(kw in text for kw in [
        "create a pptx",
        "generate a pptx",
        "create pptx",
        "generate pptx",
        "create a presentation",
        "generate a presentation",
        "create slides",
        "generate slides",
        "editable pptx",
        ".pptx",
    ])

    slide_count = None
    import re
    m = re.search(r"(\d+)\s*-?\s*slide", text)
    if m:
        slide_count = int(m.group(1))

    # return ExecutionPlan(
    #     intent="generate_artifacts" if (wants_docx_out or wants_pptx_out) else "research_only" if wants_research else "analyze_only",
    #     needs_document_analysis=has_docx or has_pdf,
    #     needs_ppt_analysis=has_pptx,
    #     needs_web_research=wants_research,
    #     needs_rag=has_docx or has_pdf or has_pptx,
    #     generate_docx=wants_docx_out,
    #     generate_pptx=wants_pptx_out,
    #     slide_count=slide_count,
    #     requires_validation=True,
    #     research_query=user_request if wants_research else None,
    #     reasoning="Heuristic plan (MockProvider active — no live LLM intent parsing).",
    # )
    
    return ExecutionPlan(
    intent="generate_artifacts" if (wants_docx_out or wants_pptx_out) else "research_only" if wants_research else "analyze_only",
    needs_document_analysis=(
    (has_docx or has_pdf or has_image)
    and (
        not wants_research
        or wants_docx_out
        or wants_pptx_out
    )
    ),
    needs_ppt_analysis=has_pptx,
    needs_web_research=wants_research,
    needs_rag=(
    wants_docx_out
    or wants_pptx_out
    ),
    generate_docx=wants_docx_out,
    generate_pptx=wants_pptx_out,
    slide_count=slide_count,
    requires_validation=True,
    research_query=user_request if wants_research else None,
    reasoning="Heuristic routing plan.",
    )


# def create_plan(user_request: str, available_files: list[dict]) -> ExecutionPlan:
#     llm = get_llm_provider()
#     if llm.name == "mock":
#         return _heuristic_plan(user_request, available_files)

#     try:
#         prompt = _build_plan_prompt(user_request, available_files)
#         result = llm.generate_json(prompt, system_prompt=PLAN_SYSTEM_PROMPT)
#         return ExecutionPlan(**result)
#     except (LLMError, LLMJSONParseError, Exception) as e:
#         logger.warning(f"LLM plan generation failed ({e}); falling back to heuristic plan.")
#         plan = _heuristic_plan(user_request, available_files)
#         plan.reasoning += f" (LLM planning failed: {e})"
#         return plan

def create_plan(user_request: str, available_files: list[dict]) -> ExecutionPlan:
    """
    Create a reliable execution plan.

    Deterministic routing is used for explicit artifact requests so that
    generation is never accidentally skipped because of an LLM intent
    classification mistake.
    """
    text = user_request.lower()

    # Always use deterministic routing for explicit artifact requests.
    explicit_docx = any(
        phrase in text
        for phrase in [
            "create a docx",
            "create docx",
            "generate a docx",
            "generate docx",
            "docx report",
            "editable docx",
            "word document",
        ]
    )

    explicit_pptx = any(
        phrase in text
        for phrase in [
            "create a pptx",
            "create pptx",
            "generate a pptx",
            "generate pptx",
            "pptx presentation",
            "editable pptx",
        ]
    )

    explicit_presentation = any(
        phrase in text
        for phrase in [
            "create a presentation",
            "generate a presentation",
            "create slides",
            "generate slides",
        ]
    )

    explicit_report = any(
        phrase in text
        for phrase in [
            "create a report",
            "generate a report",
            "create a professional report",
            "generate a professional report",
        ]
    )

    if explicit_docx or explicit_report:
        plan = _heuristic_plan(user_request, available_files)
        plan.intent = "generate_artifacts"
        plan.generate_docx = True
        plan.generate_pptx = False
        plan.needs_rag = True
        plan.needs_document_analysis = any(
            f["extension"] in (".pdf", ".docx")
            for f in available_files
        )
        plan.reasoning = "Deterministic routing: explicit DOCX generation request."
        return plan

    if explicit_pptx or explicit_presentation:
        plan = _heuristic_plan(user_request, available_files)
        plan.intent = "generate_artifacts"
        plan.generate_docx = False
        plan.generate_pptx = True
        plan.needs_rag = True
        plan.needs_document_analysis = any(
            f["extension"] in (".pdf", ".docx")
            for f in available_files
        )
        plan.needs_ppt_analysis = any(
            f["extension"] == ".pptx"
            for f in available_files
        )
        plan.reasoning = "Deterministic routing: explicit PPTX generation request."
        return plan

    # For everything else, use the deterministic planner.
    # This avoids unnecessary Gemini calls for routing.
    return _heuristic_plan(user_request, available_files)


def orchestrate(user_request: str, file_ids: list[str]) -> OrchestrationResult:
    from backend.api.ingest import _find_uploaded_file  # local import to avoid circular import at module load

    citation_registry.reset()

    # --- Inspect available files ---
    available_files = []
    file_paths: dict[str, Path] = {}
    for file_id in file_ids:
        try:
            path = _find_uploaded_file(file_id)
            file_paths[file_id] = path
            original_filename = path.name.split("_", 1)[1] if "_" in path.name else path.name
            available_files.append({"file_id": file_id, "filename": original_filename, "extension": path.suffix.lower()})
        except Exception as e:
            logger.warning(f"Could not locate uploaded file '{file_id}': {e}")

    # --- Create plan ---
    plan = create_plan(user_request, available_files)

    result = OrchestrationResult(user_request=user_request, plan=plan)

    docx_pdf_files = [f for f in available_files if f["extension"] in (".docx", ".pdf")]
    pptx_files = [f for f in available_files if f["extension"] == ".pptx"]
    image_files = [f for f in available_files if f["extension"] in (".png", ".jpg", ".jpeg")]

    # --- Document analysis ---
    if plan.needs_document_analysis and (docx_pdf_files or image_files):
        f = (docx_pdf_files + image_files)[0]
        try:
            extraction = extract_file(str(file_paths[f["file_id"]]), f["file_id"], f["filename"])
            spec = analyze_document(extraction)
            result.document_analysis = spec.model_dump()
            result.agent_calls.append(AgentCallRecord(agent="document_analyzer", status="success", detail=f["filename"]))
        except Exception as e:
            logger.exception("Document analysis failed")
            result.agent_calls.append(AgentCallRecord(agent="document_analyzer", status="failed", detail=str(e)))
            result.warnings.append(f"Document analysis failed: {e}")
    elif plan.needs_document_analysis:
        result.agent_calls.append(AgentCallRecord(agent="document_analyzer", status="skipped", detail="No DOCX/PDF/image uploaded"))

    # --- PPT analysis ---
    if plan.needs_ppt_analysis and pptx_files:
        f = pptx_files[0]
        try:
            extraction = extract_file(str(file_paths[f["file_id"]]), f["file_id"], f["filename"])
            spec = analyze_ppt(extraction, str(file_paths[f["file_id"]]))
            result.ppt_analysis = spec.model_dump()
            result.agent_calls.append(AgentCallRecord(agent="ppt_analyzer", status="success", detail=f["filename"]))
        except Exception as e:
            logger.exception("PPT analysis failed")
            result.agent_calls.append(AgentCallRecord(agent="ppt_analyzer", status="failed", detail=str(e)))
            result.warnings.append(f"PPT analysis failed: {e}")
    elif plan.needs_ppt_analysis:
        result.agent_calls.append(AgentCallRecord(agent="ppt_analyzer", status="skipped", detail="No PPTX uploaded"))

    # --- Web research ---
    if plan.needs_web_research:
        query = plan.research_query or user_request
        try:
            research_result = research(query)
            result.research = research_result.model_dump()
            status = "success" if not research_result.is_mock else "success (mock)"
            result.agent_calls.append(AgentCallRecord(agent="web_research", status=status, detail=query))
            result.warnings.extend(research_result.warnings)
        except Exception as e:
            logger.exception("Web research failed")
            result.agent_calls.append(AgentCallRecord(agent="web_research", status="failed", detail=str(e)))
            result.warnings.append(f"Web research failed: {e}")

    # --- RAG: index uploaded enterprise files, then retrieve relevant context ---
    if plan.needs_rag and (docx_pdf_files or pptx_files):
        try:
            for f in docx_pdf_files + pptx_files:
                extraction = extract_file(str(file_paths[f["file_id"]]), f["file_id"], f["filename"])
                ingest_document(extraction, document_id=f["file_id"])
            rag_result = query_knowledge_base(plan.research_query or user_request, top_k=5)
            result.rag_results = rag_result.model_dump()
            result.agent_calls.append(AgentCallRecord(agent="rag_agent", status="success", detail=f"{len(rag_result.retrieved_chunks)} chunks retrieved"))
            result.warnings.extend(rag_result.warnings)
        except Exception as e:
            logger.exception("RAG retrieval failed")
            result.agent_calls.append(AgentCallRecord(agent="rag_agent", status="failed", detail=str(e)))
            result.warnings.append(f"RAG retrieval failed: {e}")
    elif plan.needs_rag:
        result.agent_calls.append(AgentCallRecord(agent="rag_agent", status="skipped", detail="No enterprise files available to index"))

    # --- Citation summary ---
    result.citation_summary = {cid: src.__dict__ for cid, src in citation_registry.all().items()}

    # --- Generation (Phase 8/9), now wired into orchestration ---
    findings = result.research.get("findings", []) if result.research else []
    rag_chunks = result.rag_results.get("retrieved_chunks", []) if result.rag_results else []
    tone = (result.document_analysis or {}).get("tone") or (result.ppt_analysis or {}).get("visual_style") or "professional"

    if plan.generate_docx:
        try:
            content_plan = create_content_plan(user_request, research_findings=findings, rag_chunks=rag_chunks, tone=tone, document_type="report")
            artifact_id = f"doc_{uuid.uuid4().hex[:8]}"
            output_path = default_output_path(artifact_id)
            generate_docx(content_plan, output_path)
            validation = validate_docx(output_path)
            artifact_store.save_version(artifact_id, "docx", 1, output_path, content_plan, change_request=user_request)
            result.generated_docx_artifact_id = artifact_id
            result.docx_validation_status = validation.status
            result.agent_calls.append(AgentCallRecord(agent="document_generator", status="success", detail=artifact_id))
            if validation.status == "FAIL":
                result.warnings.extend([f"DOCX validation issue: {i}" for i in validation.issues])
        except Exception as e:
            logger.exception("Document generation failed")
            result.agent_calls.append(AgentCallRecord(agent="document_generator", status="failed", detail=str(e)))
            result.warnings.append(f"Document generation failed: {e}")

    if plan.generate_pptx:
        try:
            content_plan = create_content_plan(user_request, research_findings=findings, rag_chunks=rag_chunks, tone=tone, document_type="presentation")
            artifact_id = f"ppt_{uuid.uuid4().hex[:8]}"
            output_path = default_pptx_output_path(artifact_id)
            # generate_pptx(content_plan, output_path, target_slide_count=plan.slide_count)
            # validation = validate_pptx(output_path, expected_slide_count=plan.slide_count)
            generate_pptx(content_plan, output_path)
            validation = validate_pptx(output_path)
            artifact_store.save_version(artifact_id, "pptx", 1, output_path, content_plan, change_request=user_request)
            result.generated_pptx_artifact_id = artifact_id
            result.pptx_validation_status = validation.status
            result.agent_calls.append(AgentCallRecord(agent="ppt_generator", status="success", detail=artifact_id))
            if validation.status == "FAIL":
                result.warnings.extend([f"PPTX validation issue: {i}" for i in validation.issues])
        except Exception as e:
            logger.exception("Presentation generation failed")
            result.agent_calls.append(AgentCallRecord(agent="ppt_generator", status="failed", detail=str(e)))
            result.warnings.append(f"Presentation generation failed: {e}")

    # --- Next step note ---
    next_steps = []
    if plan.generate_docx and not result.generated_docx_artifact_id:
        next_steps.append("generate_docx (attempted but failed — see warnings)")
    if plan.generate_pptx and not result.generated_pptx_artifact_id:
        next_steps.append("generate_pptx (attempted but failed — see warnings)")
    result.next_step_note = "; ".join(next_steps) if next_steps else "Generation complete." if (plan.generate_docx or plan.generate_pptx) else "No generation requested by this plan."

    # --- Persist trace record ---
    result.trace_id = trace_service.create_trace(user_request, result.model_dump(exclude={"trace_id"}))

    return result

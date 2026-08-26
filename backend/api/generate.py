"""
backend/api/generate.py

POST /generate/document
Runs the content planner (using research/RAG context from a prior /chat
call would be ideal, but for a standalone endpoint we accept optional
context directly) then the Document Generation Agent, returning a
downloadable path.

For the full orchestrated flow (research -> RAG -> generate), the
Supervisor will call these functions directly in Phase 11 wiring; this
endpoint exists so DOCX/PPTX generation can be tested and used standalone.
"""
import uuid

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.agents.content_planner import create_content_plan
from backend.agents.document_generator import generate_docx, default_output_path
from backend.agents.ppt_generator import generate_pptx, default_pptx_output_path
from backend.agents.validator import validate_docx, validate_pptx
from backend.schemas.template_spec import DocumentStyleSpec, PPTStyleSpec
from backend.schemas.validation import ValidationResult
from backend.services import artifact_store

router = APIRouter(prefix="/generate", tags=["generate"])


class GenerateDocumentRequest(BaseModel):
    request: str
    research_findings: list[str] = Field(default_factory=list)
    rag_chunks: list[dict] = Field(default_factory=list)
    tone: str = "professional"
    document_type: str = "report"
    style_spec: DocumentStyleSpec | None = None
    artifact_id: str | None = None


class GenerateResponse(BaseModel):
    artifact_id: str
    file_path: str
    filename: str
    validation: ValidationResult


@router.post("/document", response_model=GenerateResponse)
def generate_document_endpoint(req: GenerateDocumentRequest) -> GenerateResponse:
    artifact_id = req.artifact_id or f"doc_{uuid.uuid4().hex[:8]}"

    plan = create_content_plan(
        user_request=req.request,
        research_findings=req.research_findings,
        rag_chunks=req.rag_chunks,
        tone=req.tone,
        document_type=req.document_type,
    )

    output_path = default_output_path(artifact_id)
    try:
        generate_docx(plan, output_path, style_spec=req.style_spec)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document generation failed: {e}")

    validation = validate_docx(output_path)

    artifact_store.save_version(
        artifact_id=artifact_id,
        artifact_type="docx",
        version=1,
        file_path=output_path,
        content_plan=plan,
        style_spec=req.style_spec.model_dump() if req.style_spec else None,
        change_request=req.request,
    )

    return GenerateResponse(artifact_id=artifact_id, file_path=output_path, filename=f"{artifact_id}.docx", validation=validation)


class GeneratePresentationRequest(BaseModel):
    request: str
    research_findings: list[str] = Field(default_factory=list)
    rag_chunks: list[dict] = Field(default_factory=list)
    tone: str = "professional"
    document_type: str = "presentation"
    slide_count: int = 8
    style_spec: PPTStyleSpec | None = None
    artifact_id: str | None = None


@router.post("/presentation", response_model=GenerateResponse)
def generate_presentation_endpoint(req: GeneratePresentationRequest) -> GenerateResponse:
    artifact_id = req.artifact_id or f"ppt_{uuid.uuid4().hex[:8]}"

    plan = create_content_plan(
        user_request=req.request,
        research_findings=req.research_findings,
        rag_chunks=req.rag_chunks,
        tone=req.tone,
        document_type=req.document_type,
    )

    output_path = default_pptx_output_path(artifact_id)
    try:
        generate_pptx(plan, output_path, style_spec=req.style_spec, target_slide_count=req.slide_count)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Presentation generation failed: {e}")

    validation = validate_pptx(output_path, expected_slide_count=req.slide_count)

    artifact_store.save_version(
        artifact_id=artifact_id,
        artifact_type="pptx",
        version=1,
        file_path=output_path,
        content_plan=plan,
        style_spec=req.style_spec.model_dump() if req.style_spec else None,
        change_request=req.request,
    )

    return GenerateResponse(artifact_id=artifact_id, file_path=output_path, filename=f"{artifact_id}.pptx", validation=validation)


@router.get("/download/{artifact_id}")
def download_artifact(artifact_id: str, ext: str = "docx"):
    from backend.config import settings
    generated_dir = settings.resolve_path(settings.generated_dir)
    matches = list(generated_dir.glob(f"{artifact_id}*.{ext}"))
    if not matches:
        raise HTTPException(status_code=404, detail=f"No generated artifact found for '{artifact_id}.{ext}'")
    return FileResponse(str(matches[0]), filename=matches[0].name)

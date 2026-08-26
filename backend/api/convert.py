"""
backend/api/convert.py

POST /convert/document-to-presentation
POST /convert/presentation-to-document
Both operate on an existing artifact_id and produce a NEW artifact (new
artifact_id), preserving the original.
"""
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services import artifact_store
from backend.services.artifact_store import ArtifactNotFoundError
from backend.agents.converter import convert_docx_to_pptx, convert_pptx_to_docx
from backend.agents.document_generator import default_output_path
from backend.agents.ppt_generator import default_pptx_output_path
from backend.agents.validator import validate_docx, validate_pptx

router = APIRouter(prefix="/convert", tags=["convert"])


class ConvertRequest(BaseModel):
    artifact_id: str
    slide_count: int | None = None  # only used for document-to-presentation


class ConvertResponse(BaseModel):
    new_artifact_id: str
    file_path: str
    validation_status: str


@router.post("/document-to-presentation", response_model=ConvertResponse)
def document_to_presentation(req: ConvertRequest) -> ConvertResponse:
    try:
        source_type = artifact_store.get_artifact_type(req.artifact_id)
        if source_type != "docx":
            raise HTTPException(status_code=400, detail=f"Source artifact is '{source_type}', expected 'docx'")
        source_plan = artifact_store.load_latest_content_plan(req.artifact_id)
        style_dict = artifact_store.get_style_spec(req.artifact_id)
    except ArtifactNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    new_id = f"{req.artifact_id}_as_pptx_{uuid.uuid4().hex[:6]}"
    output_path = default_pptx_output_path(new_id)
    _, converted_plan = convert_docx_to_pptx(source_plan, output_path, target_slide_count=req.slide_count)
    validation = validate_pptx(output_path, expected_slide_count=req.slide_count)

    artifact_store.save_version(
        artifact_id=new_id, artifact_type="pptx", version=1, file_path=output_path,
        content_plan=converted_plan, change_request=f"Converted from document artifact '{req.artifact_id}'",
    )
    return ConvertResponse(new_artifact_id=new_id, file_path=output_path, validation_status=validation.status)


@router.post("/presentation-to-document", response_model=ConvertResponse)
def presentation_to_document(req: ConvertRequest) -> ConvertResponse:
    try:
        source_type = artifact_store.get_artifact_type(req.artifact_id)
        if source_type != "pptx":
            raise HTTPException(status_code=400, detail=f"Source artifact is '{source_type}', expected 'pptx'")
        source_plan = artifact_store.load_latest_content_plan(req.artifact_id)
    except ArtifactNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    new_id = f"{req.artifact_id}_as_docx_{uuid.uuid4().hex[:6]}"
    output_path = default_output_path(new_id)
    _, converted_plan = convert_pptx_to_docx(source_plan, output_path)
    validation = validate_docx(output_path)

    artifact_store.save_version(
        artifact_id=new_id, artifact_type="docx", version=1, file_path=output_path,
        content_plan=converted_plan, change_request=f"Converted from presentation artifact '{req.artifact_id}'",
    )
    return ConvertResponse(new_artifact_id=new_id, file_path=output_path, validation_status=validation.status)

"""
backend/api/validate.py

POST /validate/{artifact_id}
Re-runs validation on a previously generated artifact by id (looks it up
in data/generated/, same pattern as /ingest and /analyze look up uploads).
"""
from fastapi import APIRouter, HTTPException

from backend.config import settings
from backend.agents.validator import validate_docx, validate_pptx
from backend.schemas.validation import ValidationResult

router = APIRouter(prefix="/validate", tags=["validate"])


@router.post("/{artifact_id}", response_model=ValidationResult)
def validate_artifact(artifact_id: str, expected_slide_count: int | None = None) -> ValidationResult:
    generated_dir = settings.resolve_path(settings.generated_dir)

    docx_matches = list(generated_dir.glob(f"{artifact_id}*.docx"))
    pptx_matches = list(generated_dir.glob(f"{artifact_id}*.pptx"))

    if docx_matches:
        return validate_docx(str(docx_matches[0]))
    if pptx_matches:
        return validate_pptx(str(pptx_matches[0]), expected_slide_count=expected_slide_count)

    raise HTTPException(status_code=404, detail=f"No generated artifact found for '{artifact_id}'")

"""
backend/api/ingest.py

POST /ingest/{file_id}
Looks up a previously uploaded file (by the file_id returned from /upload)
and runs the appropriate extractor on it, returning the normalized
ExtractionResult.

Note: file metadata isn't in a database yet (that lands in the Versioning
phase). For now we locate the file by scanning the upload directory for a
filename starting with file_id, since /upload names files "{file_id}_{original}".
"""
from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.config import settings
from backend.schemas.extraction import ExtractionResult
from backend.services.extraction_service import extract_file

router = APIRouter(prefix="/ingest", tags=["ingest"])


def _find_uploaded_file(file_id: str) -> Path:
    upload_dir = settings.resolve_path(settings.upload_dir)
    matches = list(upload_dir.glob(f"{file_id}_*"))
    if not matches:
        raise HTTPException(status_code=404, detail=f"No uploaded file found for file_id '{file_id}'")
    return matches[0]


@router.post("/{file_id}", response_model=ExtractionResult)
def ingest_file(file_id: str) -> ExtractionResult:
    file_path = _find_uploaded_file(file_id)
    original_filename = file_path.name.split("_", 1)[1] if "_" in file_path.name else file_path.name
    result = extract_file(str(file_path), file_id, original_filename)
    return result

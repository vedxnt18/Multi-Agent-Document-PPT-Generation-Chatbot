"""
backend/api/upload.py

POST /upload
Accepts a single file, validates extension + size, stores it under
data/uploads/ with a sanitized/unique filename, and returns file metadata.

This is intentionally "dumb" at this phase: no parsing, no analysis.
Phase 2 (file ingestion) will add extraction on top of this.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path

from backend.config import settings
from backend.utils.file_utils import sanitize_filename, validate_extension, validate_size
from backend.schemas.upload import UploadResponse, UploadedFileInfo

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)) -> UploadResponse:
    # --- Validate extension ---
    ok, msg = validate_extension(file.filename or "", settings.allowed_extensions_list)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)

    # --- Read into memory to check size (fine for POC-scale files; streaming
    #     to disk with a running byte counter would be the production version) ---
    contents = await file.read()
    ok, msg = validate_size(len(contents), settings.max_upload_size_bytes)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)

    # --- Store under an isolated upload directory with a sanitized name ---
    upload_dir: Path = settings.resolve_path(settings.upload_dir)
    stored_filename = sanitize_filename(file.filename or "upload")
    stored_path = upload_dir / stored_filename

    with open(stored_path, "wb") as f:
        f.write(contents)

    file_info = UploadedFileInfo(
        file_id=stored_filename.split("_", 1)[0],
        original_filename=file.filename or "unknown",
        stored_filename=stored_filename,
        stored_path=str(stored_path),
        size_bytes=len(contents),
        extension=Path(file.filename or "").suffix.lower(),
        content_type=file.content_type,
    )
    return UploadResponse(success=True, file=file_info)

"""
backend/schemas/upload.py

Typed request/response schemas for the upload API. Kept separate from
models/ (which will hold DB-mapped models in a later phase).
"""
from pydantic import BaseModel


class UploadedFileInfo(BaseModel):
    file_id: str
    original_filename: str
    stored_filename: str
    stored_path: str
    size_bytes: int
    extension: str
    content_type: str | None = None


class UploadResponse(BaseModel):
    success: bool
    file: UploadedFileInfo | None = None
    error: str | None = None

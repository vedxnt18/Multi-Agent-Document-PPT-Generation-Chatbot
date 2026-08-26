"""
backend/services/extraction_service.py

Single entrypoint that routes a file to the correct extractor based on its
extension. This is the "FILE TYPE DETECTION" step in the ingestion pipeline
described in the assignment.
"""
from pathlib import Path

from backend.schemas.extraction import ExtractionResult
from backend.services.document_service import extract_pdf, extract_docx, extract_image
from backend.services.ppt_service import extract_pptx

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def extract_file(file_path: str, file_id: str, original_filename: str) -> ExtractionResult:
    ext = Path(file_path).suffix.lower()

    if ext == ".pdf":
        return extract_pdf(file_path, file_id, original_filename)
    if ext == ".docx":
        return extract_docx(file_path, file_id, original_filename)
    if ext == ".pptx":
        return extract_pptx(file_path, file_id, original_filename)
    if ext in IMAGE_EXTENSIONS:
        return extract_image(file_path, file_id, original_filename)

    # Should not normally happen since /upload already validates extensions,
    # but fail clearly rather than silently if it does.
    result = ExtractionResult(
        file_id=file_id,
        original_filename=original_filename,
        file_extension=ext,
        document_type="unknown",
    )
    result.warnings.append(f"No extractor available for file extension '{ext}'.")
    return result

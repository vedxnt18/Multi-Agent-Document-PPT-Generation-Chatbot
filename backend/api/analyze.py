"""
backend/api/analyze.py

POST /analyze/{file_id}
Runs extraction (Phase 2) then the appropriate analysis agent (Phase 3) on
a previously uploaded file, returning a DocumentStyleSpec or PPTStyleSpec
depending on file type. Images/PDFs-without-structure return a 422 since
"template analysis" isn't a meaningful operation for those.
"""
from fastapi import APIRouter, HTTPException

from backend.api.ingest import _find_uploaded_file
from backend.services.extraction_service import extract_file
from backend.agents.document_analyzer import analyze_document
from backend.agents.ppt_analyzer import analyze_ppt

router = APIRouter(prefix="/analyze", tags=["analyze"])


@router.post("/{file_id}")
def analyze_file(file_id: str):
    file_path = _find_uploaded_file(file_id)
    original_filename = file_path.name.split("_", 1)[1] if "_" in file_path.name else file_path.name

    extraction = extract_file(str(file_path), file_id, original_filename)

    if extraction.document_type == "docx":
        return analyze_document(extraction)
    elif extraction.document_type == "pptx":
        return analyze_ppt(extraction, str(file_path))
    elif extraction.document_type == "pdf":
        # PDFs are analyzable with the same document analyzer (headings from
        # PyMuPDF text blocks are less reliable than DOCX styles, but the
        # structural facts we do have still apply).
        return analyze_document(extraction)
    else:
        raise HTTPException(
            status_code=422,
            detail=f"Template analysis is not applicable to document_type '{extraction.document_type}'.",
        )
